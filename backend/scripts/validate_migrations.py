#!/usr/bin/env python
"""
Alembic Migration Validation Script

This script validates the Alembic migration chain to ensure:
1. No duplicate migrations
2. No broken revision chains
3. All migrations have valid up/down functions
4. No orphaned migrations (migrations without parents except the initial one)

Usage:
    python scripts/validate_migrations.py

Exit codes:
    0 - All validations passed
    1 - Validation errors found
"""

import re
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def get_migrations_dir() -> Path:
    """Get the path to the migrations directory."""
    return backend_dir / "alembic" / "versions"


def parse_migration_file(filepath: Path) -> dict | None:
    """
    Parse a migration file and extract revision information.

    Args:
        filepath: Path to the migration file

    Returns:
        Dictionary with revision info or None if parsing failed
    """
    try:
        content = filepath.read_text(encoding="utf-8")

        # Extract revision ID
        revision_match = re.search(
            r"^revision(?:\s*:\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE
        )

        # Extract down_revision (handle various type annotations)
        down_revision_raw = "None"
        for line in content.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith("down_revision") and "=" in stripped_line:
                down_revision_raw = stripped_line.split("=", 1)[1].strip()
                break

        # Check for upgrade function
        has_upgrade = "def upgrade(" in content or "def upgrade()->" in content

        # Check for downgrade function
        has_downgrade = "def downgrade(" in content or "def downgrade()->" in content

        if not revision_match:
            return None

        revision = revision_match.group(1)

        # Parse down_revision (can be None, string, or tuple)
        if down_revision_raw == "None":
            down_revision = None
        elif down_revision_raw.startswith("("):
            # Handle tuple (merge migration)
            tuples = re.findall(r"['\"]([^'\"]+)['\"]", down_revision_raw)
            down_revision = tuple(tuples)
        else:
            # Single parent
            string_match = re.search(r"['\"]([^'\"]+)['\"]", down_revision_raw)
            down_revision = string_match.group(1) if string_match else None

        return {
            "file": filepath.name,
            "revision": revision,
            "down_revision": down_revision,
            "has_upgrade": has_upgrade,
            "has_downgrade": has_downgrade,
        }

    except Exception as e:
        print(f"  ⚠️  Error parsing {filepath.name}: {e}")
        return None


def _check_broken_chains(migrations: list[dict], all_revisions: set[str]) -> list[str]:
    errors = []
    for migration in migrations:
        down_rev = migration["down_revision"]
        if down_rev is None:
            continue
        if isinstance(down_rev, tuple):
            for parent in down_rev:
                if parent not in all_revisions:
                    errors.append(
                        f"Broken chain: '{migration['revision']}' references non-existent parent '{parent}'"
                    )
        elif down_rev not in all_revisions:
            errors.append(
                f"Broken chain: '{migration['revision']}' references non-existent parent '{down_rev}'"
            )
    return errors


def _check_missing_functions(migrations: list[dict]) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []
    for migration in migrations:
        if not migration["has_upgrade"]:
            errors.append(f"Missing upgrade() function in {migration['file']}")
        if not migration["has_downgrade"]:
            warnings.append(f"Missing downgrade() function in {migration['file']}")
    return errors, warnings


def validate_migration_chain(migrations: list[dict]) -> tuple[bool, list[str]]:
    """
    Validate the migration chain for issues.

    Args:
        migrations: List of parsed migration dictionaries

    Returns:
        Tuple of (success, list of error messages)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Build revision lookup
    revision_to_migration: dict[str, dict] = {}
    all_revisions: set[str] = set()

    for migration in migrations:
        rev = migration["revision"]
        if rev in all_revisions:
            errors.append(f"Duplicate revision ID: '{rev}' in {migration['file']}")
        all_revisions.add(rev)
        revision_to_migration[rev] = migration

    # Check for broken chains
    errors.extend(_check_broken_chains(migrations, all_revisions))

    # Check for missing upgrade/downgrade
    missing_errors, missing_warnings = _check_missing_functions(migrations)
    errors.extend(missing_errors)
    warnings.extend(missing_warnings)

    # Count initial migrations (should be exactly 1)
    initial_migrations = [m for m in migrations if m["down_revision"] is None]
    if len(initial_migrations) == 0:
        errors.append("No initial migration found (down_revision = None)")
    elif len(initial_migrations) > 1:
        names = [m["file"] for m in initial_migrations]
        warnings.append(f"Multiple initial migrations found: {', '.join(names)}")

    # Check for naming consistency
    date_pattern = re.compile(r"^\d{4}_\d{2}_\d{2}_")
    hash_pattern = re.compile(r"^[a-f0-9]{12}_")
    custom_pattern = re.compile(r"^[a-z_]+\d{3}_")

    naming_styles = {"date": [], "hash": [], "custom": [], "other": []}

    for migration in migrations:
        filename = migration["file"]
        if date_pattern.match(filename):
            naming_styles["date"].append(filename)
        elif hash_pattern.match(filename):
            naming_styles["hash"].append(filename)
        elif custom_pattern.match(filename):
            naming_styles["custom"].append(filename)
        else:
            naming_styles["other"].append(filename)

    non_empty_styles = [k for k, v in naming_styles.items() if v]
    if len(non_empty_styles) > 1:
        style_counts = {k: len(v) for k, v in naming_styles.items() if v}
        warnings.append(f"Inconsistent file naming: {style_counts}")

    # Print warnings
    for warning in warnings:
        print(f"  ⚠️  {warning}")

    return len(errors) == 0, errors


def _is_safe_table_creation(content: str, table: str) -> bool:
    """Return whether a table creation is guarded by an existence check."""
    markers = (
        f"table_exists('{table}')",
        f'table_exists("{table}")',
        f"safe_create_table('{table}'",
        f'safe_create_table("{table}"',
    )
    return any(marker in content for marker in markers)


def _read_table_creations(migration: dict, migrations_dir: Path) -> list[tuple[str, bool]]:
    """Read table creations from one migration, ignoring unreadable files."""
    filepath = migrations_dir / migration["file"]
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    tables = re.findall(
        r"(?:op\.create_table|safe_create_table)\s*\(\s*['\"]([^'\"]+)['\"]", content
    )
    return [(table, _is_safe_table_creation(content, table)) for table in tables]


def _duplicate_table_warnings(table: str, file_info: list[tuple[str, bool]]) -> list[str]:
    """Build warnings for repeated table creation across migrations."""
    unsafe_files = [filename for filename, is_safe in file_info if not is_safe]
    safe_files = [filename for filename, is_safe in file_info if is_safe]
    if len(unsafe_files) > 1:
        return [f"Table '{table}' has unguarded creation in multiple migrations: {unsafe_files}"]
    if len(unsafe_files) == 1 and safe_files:
        all_files = [filename for filename, _ in file_info]
        return [
            f"Table '{table}' is referenced in multiple migrations: {all_files} (guarded with table_exists check)"
        ]
    return []


def check_duplicate_tables(migrations: list[dict], migrations_dir: Path) -> list[str]:
    """
    Check for potential duplicate table/column creation.

    Args:
        migrations: List of parsed migration dictionaries
        migrations_dir: Path to migrations directory

    Returns:
        List of warning messages
    """
    warnings = []
    table_creations: dict[str, list[tuple[str, bool]]] = {}  # table -> [(file, is_safe), ...]

    for migration in migrations:
        for table, is_safe in _read_table_creations(migration, migrations_dir):
            table_creations.setdefault(table, []).append((migration["file"], is_safe))

    for table, file_info in table_creations.items():
        if len(file_info) > 1:
            warnings.extend(_duplicate_table_warnings(table, file_info))

    return warnings


def main() -> int:
    """Main validation function."""
    print("=" * 60)
    print("🔍 Alembic Migration Validation")
    print("=" * 60)
    print()

    migrations_dir = get_migrations_dir()

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return 1

    # Find all migration files
    migration_files = list(migrations_dir.glob("*.py"))
    migration_files = [f for f in migration_files if not f.name.startswith("__")]

    print(f"📁 Found {len(migration_files)} migration files")
    print()

    # Parse all migrations
    print("📋 Parsing migrations...")
    migrations = []
    for filepath in migration_files:
        result = parse_migration_file(filepath)
        if result:
            migrations.append(result)
            print(f"  ✓ {result['revision']}: {result['file']}")
        else:
            print(f"  ✗ Failed to parse: {filepath.name}")

    print()

    # Validate chain
    print("🔗 Validating migration chain...")
    success, errors = validate_migration_chain(migrations)

    if errors:
        print()
        print("❌ Validation errors:")
        for error in errors:
            print(f"  • {error}")

    print()

    # Check for duplicate tables
    print("📊 Checking for duplicate table creations...")
    table_warnings = check_duplicate_tables(migrations, migrations_dir)

    if table_warnings:
        for warning in table_warnings:
            print(f"  ⚠️  {warning}")
    else:
        print("  ✓ No duplicate table creations detected")

    print()
    print("=" * 60)

    if success and not errors:
        print("✅ All validations passed!")
        return 0
    else:
        print("❌ Validation failed - please fix the errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
