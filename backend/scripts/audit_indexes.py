"""
Database Index Audit and Recommendation Script.
Analyzes query patterns and suggests optimal indexes.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal


@dataclass
class IndexRecommendation:
    """Represents an index recommendation."""

    table_name: str
    column_names: list[str]
    index_name: str
    reason: str
    priority: str  # high, medium, low
    create_statement: str


@dataclass
class ExistingIndex:
    """Represents an existing database index."""

    index_name: str
    table_name: str
    column_names: list[str]
    is_unique: bool
    is_primary: bool


async def get_existing_indexes(session: AsyncSession) -> list[ExistingIndex]:
    """Fetch all existing indexes from the database."""
    query = text("""
        SELECT
            i.relname as index_name,
            t.relname as table_name,
            array_agg(a.attname ORDER BY k.n) as column_names,
            ix.indisunique as is_unique,
            ix.indisprimary as is_primary
        FROM pg_index ix
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, n) ON true
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
        WHERE n.nspname = 'public'
        AND t.relkind = 'r'
        GROUP BY i.relname, t.relname, ix.indisunique, ix.indisprimary
        ORDER BY t.relname, i.relname;
    """)

    result = await session.execute(query)
    rows = result.fetchall()

    indexes = []
    for row in rows:
        indexes.append(
            ExistingIndex(
                index_name=row[0],
                table_name=row[1],
                column_names=row[2],
                is_unique=row[3],
                is_primary=row[4],
            )
        )

    return indexes


async def get_table_statistics(session: AsyncSession) -> dict[str, Any]:
    """Get table statistics including row counts and sizes."""
    query = text("""
        SELECT
            relname as table_name,
            n_live_tup as row_count,
            pg_size_pretty(pg_total_relation_size(relid)) as total_size,
            pg_size_pretty(pg_indexes_size(relid)) as index_size,
            seq_scan,
            idx_scan
        FROM pg_stat_user_tables
        ORDER BY n_live_tup DESC;
    """)

    result = await session.execute(query)
    rows = result.fetchall()

    stats = {}
    for row in rows:
        stats[row[0]] = {
            "row_count": row[1],
            "total_size": row[2],
            "index_size": row[3],
            "seq_scans": row[4],
            "idx_scans": row[5],
        }

    return stats


async def get_slow_queries(session: AsyncSession, min_calls: int = 10) -> list[dict[str, Any]]:
    """Get slow queries from pg_stat_statements if available."""
    try:
        query = text("""
            SELECT
                substring(query, 1, 200) as query_preview,
                calls,
                round(total_exec_time::numeric / calls, 2) as avg_time_ms,
                round(total_exec_time::numeric, 2) as total_time_ms,
                rows
            FROM pg_stat_statements
            WHERE calls >= :min_calls
            AND query NOT LIKE '%pg_%'
            ORDER BY total_exec_time DESC
            LIMIT 20;
        """)

        result = await session.execute(query, {"min_calls": min_calls})
        rows = result.fetchall()

        return [
            {
                "query": row[0],
                "calls": row[1],
                "avg_time_ms": float(row[2]),
                "total_time_ms": float(row[3]),
                "rows": row[4],
            }
            for row in rows
        ]
    except Exception:
        print("Note: pg_stat_statements extension not available")
        return []


async def get_missing_fk_indexes(session: AsyncSession) -> list[dict[str, Any]]:
    """Find public-schema foreign keys without a left-prefix covering index."""
    query = text("""
        WITH foreign_keys AS (
            SELECT
                c.conrelid,
                c.confrelid,
                c.conkey,
                c.conrelid::regclass::text AS table_name,
                c.confrelid::regclass::text AS referenced_table,
                array_agg(a.attname ORDER BY key_columns.ordinality) AS column_names
            FROM pg_constraint c
            JOIN pg_namespace source_schema
              ON source_schema.oid = c.connamespace
            CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY
              AS key_columns(attnum, ordinality)
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid
             AND a.attnum = key_columns.attnum
            WHERE c.contype = 'f'
              AND source_schema.nspname = 'public'
            GROUP BY c.oid, c.conrelid, c.confrelid, c.conkey
        ), indexes AS (
            SELECT
                i.indrelid,
                array_agg(index_columns.attnum ORDER BY index_columns.ordinality) AS column_numbers
            FROM pg_index i
            CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY
              AS index_columns(attnum, ordinality)
            WHERE i.indpred IS NULL
              AND i.indexprs IS NULL
            GROUP BY i.indexrelid, i.indrelid
        )
        SELECT
            foreign_keys.table_name,
            array_to_string(foreign_keys.column_names, ',') AS column_name,
            foreign_keys.referenced_table
        FROM foreign_keys
        WHERE NOT EXISTS (
            SELECT 1
            FROM indexes
            WHERE indexes.indrelid = foreign_keys.conrelid
              AND indexes.column_numbers[1:cardinality(foreign_keys.conkey)] = foreign_keys.conkey
        )
        ORDER BY foreign_keys.table_name, column_name;
    """)

    result = await session.execute(query)
    rows = result.fetchall()

    return [
        {
            "table_name": row[0],
            "column_name": row[1],
            "referenced_table": row[2],
        }
        for row in rows
    ]


async def get_unused_indexes(
    session: AsyncSession, min_size_bytes: int = 1024
) -> list[dict[str, Any]]:
    """Find indexes that are rarely or never used."""
    query = text("""
        SELECT
            schemaname,
            relname as table_name,
            indexrelname as index_name,
            idx_scan,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
            pg_relation_size(indexrelid) as index_size_bytes
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        AND pg_relation_size(indexrelid) > :min_size
        AND indexrelname NOT LIKE '%_pkey'
        ORDER BY pg_relation_size(indexrelid) DESC;
    """)

    result = await session.execute(query, {"min_size": min_size_bytes})
    rows = result.fetchall()

    return [
        {
            "schema": row[0],
            "table_name": row[1],
            "index_name": row[2],
            "scan_count": row[3],
            "size": row[4],
        }
        for row in rows
    ]


def generate_recommendations(
    existing_indexes: list[ExistingIndex],
    table_stats: dict[str, Any],
    missing_fk_indexes: list[dict[str, Any]],
) -> list[IndexRecommendation]:
    """Generate index recommendations based on analysis."""
    recommendations = []

    # Common query patterns in Insight-Flow that benefit from indexes
    suggested_indexes = [
        # Tasks table
        {
            "table": "tasks",
            "columns": ["project_id", "status"],
            "reason": "Task filtering by project and status",
        },
        {
            "table": "tasks",
            "columns": ["assignee_id", "status"],
            "reason": "Task filtering by assignee and status",
        },
        {"table": "tasks", "columns": ["due_date"], "reason": "Deadline queries and ordering"},
        {"table": "tasks", "columns": ["created_at"], "reason": "Recent tasks ordering"},
        {"table": "tasks", "columns": ["priority"], "reason": "Priority-based filtering"},
        # Projects table
        {
            "table": "projects",
            "columns": ["owner_id", "is_active"],
            "reason": "User's active projects",
        },
        {"table": "projects", "columns": ["created_at"], "reason": "Recent projects ordering"},
        # Users table
        {"table": "users", "columns": ["email"], "reason": "Login and user lookup"},
        {"table": "users", "columns": ["is_active"], "reason": "Active user filtering"},
        # Project members table
        {
            "table": "project_members",
            "columns": ["user_id", "project_id"],
            "reason": "Membership lookups",
        },
        {
            "table": "project_members",
            "columns": ["project_id", "role"],
            "reason": "Role-based access",
        },
        # Notifications table
        {
            "table": "notifications",
            "columns": ["user_id", "is_read"],
            "reason": "Unread notifications",
        },
        {
            "table": "notifications",
            "columns": ["user_id", "created_at"],
            "reason": "Recent notifications",
        },
        # Task history table
        {"table": "task_history", "columns": ["task_id", "created_at"], "reason": "Task timeline"},
        {"table": "task_history", "columns": ["user_id"], "reason": "User activity"},
        # Token blacklist
        {
            "table": "token_blacklist",
            "columns": ["expires_at"],
            "reason": "Expired-token cleanup",
        },
    ]

    # Check which suggested indexes don't exist
    existing_index_keys = set()
    for idx in existing_indexes:
        key = f"{idx.table_name}:{','.join(idx.column_names)}"
        existing_index_keys.add(key)

    for suggestion in suggested_indexes:
        key = f"{suggestion['table']}:{','.join(suggestion['columns'])}"

        # Check if table exists in stats
        if suggestion["table"] not in table_stats:
            continue

        # Check if similar index exists
        if key not in existing_index_keys:
            columns_str = "_".join(suggestion["columns"])
            index_name = f"ix_{suggestion['table']}_{columns_str}"
            columns_list = ", ".join(suggestion["columns"])

            recommendations.append(
                IndexRecommendation(
                    table_name=suggestion["table"],
                    column_names=suggestion["columns"],
                    index_name=index_name,
                    reason=suggestion["reason"],
                    priority="high" if "id" in columns_str or "status" in columns_str else "medium",
                    create_statement=f"CREATE INDEX {index_name} ON {suggestion['table']} ({columns_list});",
                )
            )

    # Add recommendations for missing FK indexes
    for fk in missing_fk_indexes:
        index_name = f"ix_{fk['table_name']}_{fk['column_name']}"
        recommendations.append(
            IndexRecommendation(
                table_name=fk["table_name"],
                column_names=[fk["column_name"]],
                index_name=index_name,
                reason=f"Foreign key to {fk['referenced_table']} (improve JOIN performance)",
                priority="high",
                create_statement=f"CREATE INDEX {index_name} ON {fk['table_name']} ({fk['column_name']});",
            )
        )

    return recommendations


async def _audit_existing_indexes(session: AsyncSession) -> list[ExistingIndex]:
    print("\n📊 EXISTING INDEXES")
    print("-" * 40)
    existing_indexes = await get_existing_indexes(session)
    for idx in existing_indexes:
        if idx.is_primary:
            prefix = "🔑"
        elif idx.is_unique:
            prefix = "🔒"
        else:
            prefix = "📌"
        print(f"{prefix} {idx.table_name}.{idx.index_name}: ({', '.join(idx.column_names)})")
    return existing_indexes


async def _audit_table_statistics(session: AsyncSession) -> dict[str, Any]:
    print("\n📈 TABLE STATISTICS")
    print("-" * 40)
    table_stats = await get_table_statistics(session)
    print(f"{'Table':<25} {'Rows':<10} {'Size':<12} {'Seq Scans':<12} {'Idx Scans'}")
    print("-" * 80)
    for table, stats in table_stats.items():
        print(
            f"{table:<25} {stats['row_count']:<10} {stats['total_size']:<12} "
            f"{stats['seq_scans']:<12} {stats['idx_scans']}"
        )
    return table_stats


async def _audit_missing_foreign_keys(session: AsyncSession) -> list[dict[str, Any]]:
    print("\n⚠️  MISSING FOREIGN KEY INDEXES")
    print("-" * 40)
    missing_fk_indexes = await get_missing_fk_indexes(session)
    if missing_fk_indexes:
        for fk in missing_fk_indexes:
            print(f"  • {fk['table_name']}.{fk['column_name']} → {fk['referenced_table']}")
    else:
        print("  ✅ All foreign keys have indexes")
    return missing_fk_indexes


async def _audit_unused_indexes(session: AsyncSession) -> list[dict[str, Any]]:
    print("\n🗑️  UNUSED INDEXES (candidates for removal)")
    print("-" * 40)
    unused_indexes = await get_unused_indexes(session)
    if unused_indexes:
        for idx in unused_indexes:
            print(
                f"  • {idx['table_name']}.{idx['index_name']} "
                f"(Size: {idx['size']}, Scans: {idx['scan_count']})"
            )
    else:
        print("  ✅ All indexes are being used")
    return unused_indexes


async def _audit_slow_queries(session: AsyncSession) -> None:
    print("\n🐢 SLOW QUERIES (from pg_stat_statements)")
    print("-" * 40)
    slow_queries = await get_slow_queries(session)
    if slow_queries:
        for i, query in enumerate(slow_queries[:5], 1):
            print(f"\n  {i}. Avg Time: {query['avg_time_ms']}ms, Calls: {query['calls']}")
            print(f"     {query['query'][:100]}...")
    else:
        print("  [i] pg_stat_statements not available or no slow queries")


def _print_recommendations(recommendations: list[IndexRecommendation]) -> None:
    if not recommendations:
        print("  ✅ No additional indexes recommended")
        return

    priorities = (
        ("high", "🔴 HIGH PRIORITY"),
        ("medium", "🟡 MEDIUM PRIORITY"),
    )
    for priority, label in priorities:
        matching = [rec for rec in recommendations if rec.priority == priority]
        if matching:
            print(f"\n  {label}:")
            for rec in matching:
                print(f"\n    Table: {rec.table_name}")
                print(f"    Columns: {', '.join(rec.column_names)}")
                print(f"    Reason: {rec.reason}")
                print(f"    SQL: {rec.create_statement}")


async def run_audit():
    """Run the complete index audit."""
    print("=" * 60)
    print("DATABASE INDEX AUDIT")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        existing_indexes = await _audit_existing_indexes(session)
        table_stats = await _audit_table_statistics(session)
        missing_fk_indexes = await _audit_missing_foreign_keys(session)
        await _audit_unused_indexes(session)
        await _audit_slow_queries(session)

        print("\n💡 INDEX RECOMMENDATIONS")
        print("-" * 40)
        recommendations = generate_recommendations(
            existing_indexes, table_stats, missing_fk_indexes
        )
        _print_recommendations(recommendations)

        # Generate migration file
        print("\n📝 MIGRATION FILE")
        print("-" * 40)
        if recommendations:
            migration_content = generate_migration_file(recommendations)
            print(
                f"  Migration file content generated ({len(migration_content)} chars). Run with --generate-migration to save."
            )

        print("\n" + "=" * 60)
        print("AUDIT COMPLETE")
        print("=" * 60)


def generate_migration_file(recommendations: list[IndexRecommendation]) -> str:
    """Generate an Alembic migration file content."""
    upgrade_statements = []
    downgrade_statements = []

    for rec in recommendations:
        upgrade_statements.append(
            f'    op.create_index("{rec.index_name}", "{rec.table_name}", {rec.column_names})'
        )
        downgrade_statements.append(
            f'    op.drop_index("{rec.index_name}", table_name="{rec.table_name}")'
        )

    return f'''"""Add performance indexes based on audit

Revision ID: auto_generated
Revises:
Create Date: {datetime.now().isoformat()}
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
{chr(10).join(upgrade_statements)}


def downgrade():
{chr(10).join(downgrade_statements)}
'''


if __name__ == "__main__":
    asyncio.run(run_audit())
