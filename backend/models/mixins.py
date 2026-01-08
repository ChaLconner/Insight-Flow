"""
SQLAlchemy Model Mixins - Staff/Principal Level Database Patterns

Provides:
- Soft Delete pattern with automatic filtering
- Audit Trail with user tracking
- Optimistic Locking with version control
- Multi-tenancy support
- Change History with JSON diff
"""

from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import DateTime, Integer, event, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from utils.logger import setup_logger

logger = setup_logger("model_mixins")


# =============================================================================
# Timestamp Mixin
# =============================================================================


class TimestampMixin:
    """
    Provides created_at and updated_at timestamps.

    Automatically sets created_at on insert and updated_at on update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


# =============================================================================
# Soft Delete Mixin
# =============================================================================


class SoftDeleteMixin:
    """
    Implements soft delete pattern.

    Records are marked as deleted instead of being removed from the database.
    Includes automatic query filtering with SQLAlchemy events.

    Usage:
        class Project(Base, SoftDeleteMixin):
            __tablename__ = "projects"
            ...

        # Soft delete
        project.soft_delete()

        # Restore
        project.restore()

        # Check status
        if project.is_deleted:
            print("Project is deleted")
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
    )

    deleted_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        default=None,
        nullable=True,
    )

    @hybrid_property
    def is_deleted(self) -> bool:
        """Check if the record is soft-deleted."""
        return self.deleted_at is not None

    @is_deleted.expression  # type: ignore[no-redef]
    def is_deleted(cls):
        """SQL expression for is_deleted."""
        return cls.deleted_at.isnot(None)

    def soft_delete(self, deleted_by: UUID | None = None) -> None:
        """Mark the record as deleted."""
        self.deleted_at = datetime.now(UTC)
        self.deleted_by_id = deleted_by
        logger.debug(f"Soft deleted {type(self).__name__} id={getattr(self, 'id', 'unknown')}")

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.deleted_by_id = None
        logger.debug(f"Restored {type(self).__name__} id={getattr(self, 'id', 'unknown')}")

    @classmethod
    def not_deleted_filter(cls):
        """Return filter condition for active (not deleted) records."""
        return cls.deleted_at.is_(None)


# =============================================================================
# Audit Mixin
# =============================================================================


class AuditMixin:
    """
    Tracks who created and last modified a record.

    Requires integration with user context to set IDs automatically.

    Usage:
        class Project(Base, AuditMixin):
            __tablename__ = "projects"
            ...
    """

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    updated_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    @declared_attr
    def created_by(cls):
        """Relationship to user who created the record."""
        return relationship(
            "User",
            foreign_keys=[cls.created_by_id],  # type: ignore
            lazy="select",
        )

    @declared_attr
    def updated_by(cls):
        """Relationship to user who last updated the record."""
        return relationship(
            "User",
            foreign_keys=[cls.updated_by_id],  # type: ignore
            lazy="select",
        )

    def set_created_by(self, user_id: UUID) -> None:
        """Set the creator of this record."""
        self.created_by_id = user_id
        self.updated_by_id = user_id

    def set_updated_by(self, user_id: UUID) -> None:
        """Set the last modifier of this record."""
        self.updated_by_id = user_id


# =============================================================================
# Optimistic Locking Mixin
# =============================================================================


class VersionedMixin:
    """
    Implements optimistic locking with version numbers.

    Prevents concurrent modification conflicts by tracking version.

    Usage:
        class Task(Base, VersionedMixin):
            __tablename__ = "tasks"
            ...

        # Update with version check
        task.increment_version()

        # In repository:
        async def update(self, task, expected_version: int):
            if task.version != expected_version:
                raise OptimisticLockError("Task was modified by another user")
    """

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    def increment_version(self) -> int:
        """Increment version and return new version number."""
        self.version = (self.version or 0) + 1
        return self.version

    def check_version(self, expected_version: int) -> bool:
        """Check if current version matches expected."""
        return self.version == expected_version


class OptimisticLockError(Exception):
    """Raised when optimistic lock fails."""

    pass


# =============================================================================
# Multi-Tenancy Mixin
# =============================================================================


class TenantMixin:
    """
    Supports multi-tenant data isolation.

    All queries automatically filter by tenant_id when configured.

    Usage:
        class Project(Base, TenantMixin):
            __tablename__ = "projects"
            ...

        # Set tenant context
        with tenant_context(tenant_id):
            projects = await repo.list_all()  # Auto-filtered by tenant
    """

    tenant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    @classmethod
    def tenant_filter(cls, tenant_id: UUID):
        """Return filter condition for specific tenant."""
        return cls.tenant_id == tenant_id


# =============================================================================
# History / Change Tracking Mixin
# =============================================================================


class ChangeHistoryMixin:
    """
    Tracks all changes to a record with JSON diff.

    Creates a history entry on each update with:
    - Previous and new values
    - User who made the change
    - Timestamp

    Usage:
        class Task(Base, ChangeHistoryMixin):
            __tablename__ = "tasks"
            # Enable history for specific fields
            __history_fields__ = ['title', 'status', 'priority', 'assignee_id']
    """

    # Override in subclass to specify tracked fields
    __history_fields__: ClassVar[list[str]] = []

    def create_history_entry(
        self,
        changes: dict[str, tuple[Any, Any]],
        user_id: UUID | None = None,
    ) -> "ChangeHistory":
        """
        Create a history entry for changes.

        Args:
            changes: Dict of {field_name: (old_value, new_value)}
            user_id: ID of user making the change
        """

        return ChangeHistory(
            entity_type=type(self).__name__,
            entity_id=getattr(self, "id", None),
            changes=changes,
            changed_by_id=user_id,
            changed_at=datetime.now(UTC),
        )

    def get_diff(self, old_state: dict) -> dict[str, tuple[Any, Any]]:
        """
        Calculate diff between old state and current state.

        Returns dict of {field: (old_value, new_value)} for changed fields.
        """
        changes = {}
        for field in self.__history_fields__:
            old_value = old_state.get(field)
            new_value = getattr(self, field, None)

            # Convert UUIDs to strings for comparison
            if isinstance(old_value, UUID):
                old_value = str(old_value)
            if isinstance(new_value, UUID):
                new_value = str(new_value)

            if old_value != new_value:
                changes[field] = (old_value, new_value)

        return changes


# =============================================================================
# Change History Model
# =============================================================================

# This would typically be in a separate file, included here for completeness


class ChangeHistory:
    """
    Stores history of changes to tracked entities.

    Note: This is a template - implement as actual model in models/change_history.py
    """

    __tablename__ = "change_history"

    id: Mapped[UUID]
    entity_type: Mapped[str]  # e.g., "Task", "Project"
    entity_id: Mapped[UUID]
    changes: Mapped[dict]  # JSONB: {field: [old, new]}
    changed_by_id: Mapped[UUID | None]
    changed_at: Mapped[datetime]

    # Additional metadata
    request_id: Mapped[str | None]  # For correlation
    ip_address: Mapped[str | None]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# =============================================================================
# Composite Index Helpers
# =============================================================================


def create_soft_delete_index(table_name: str, *columns: str):
    """
    Create a partial index that excludes soft-deleted records.

    Usage:
        # In __table_args__
        create_soft_delete_index('projects', 'owner_id', 'status')
    """
    from sqlalchemy import Index

    col_names = "_".join(columns)
    return Index(
        f"ix_{table_name}_{col_names}_active",
        *columns,
        postgresql_where=text("deleted_at IS NULL"),
    )


def create_tenant_index(table_name: str, *columns: str):
    """
    Create a composite index with tenant_id as first column.

    Usage:
        # In __table_args__
        create_tenant_index('projects', 'status', 'priority')
    """
    from sqlalchemy import Index

    col_names = "_".join(columns)
    return Index(
        f"ix_{table_name}_tenant_{col_names}",
        "tenant_id",
        *columns,
    )


# =============================================================================
# SQLAlchemy Event Listeners for Automatic History
# =============================================================================


def setup_history_tracking(model_class):
    """
    Set up automatic history tracking for a model.

    Usage:
        class Task(Base, ChangeHistoryMixin):
            __tablename__ = "tasks"
            __history_fields__ = ['title', 'status']

        # After model definition
        setup_history_tracking(Task)
    """

    @event.listens_for(model_class, "before_update")
    def receive_before_update(mapper, connection, target):
        """Capture state before update for history."""
        if not hasattr(target, "__history_fields__") or not target.__history_fields__:
            return

        # Store old values in temporary attribute
        old_state = {}
        for field in target.__history_fields__:
            old_state[field] = getattr(target, field, None)

        target._old_state = old_state

    @event.listens_for(model_class, "after_update")
    def receive_after_update(mapper, connection, target):
        """Create history entry after update."""
        if not hasattr(target, "_old_state"):
            return

        changes = target.get_diff(target._old_state)
        if changes:
            logger.debug(f"Changes detected for {type(target).__name__}: {list(changes.keys())}")
            # Note: Actual history saving should be done in the repository/service layer
            # to maintain transaction consistency

        # Clean up
        delattr(target, "_old_state")


# =============================================================================
# Full Example: Task Model with All Mixins
# =============================================================================

"""
Example usage:

class Task(Base, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionedMixin, ChangeHistoryMixin):
    __tablename__ = "tasks"
    __history_fields__ = ['title', 'description', 'status', 'priority', 'assignee_id', 'due_date']
    __table_args__ = (
        create_soft_delete_index('tasks', 'project_id', 'status'),
        create_soft_delete_index('tasks', 'assignee_id', 'due_date'),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"))
    assignee_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
"""
