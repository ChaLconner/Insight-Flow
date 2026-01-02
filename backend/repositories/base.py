"""
Base Repository Pattern implementation for data access abstraction.
Provides a clean separation between business logic and database operations.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from models import BaseModel

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository[ModelType: BaseModel](ABC):
    """
    Abstract base repository defining the interface for data access operations.
    Implements common CRUD operations that can be extended or overridden.
    """

    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """Get a single entity by ID."""
        pass

    @abstractmethod
    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """Get all entities with optional pagination and filtering."""
        pass

    @abstractmethod
    async def create(self, entity: ModelType) -> ModelType:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, id: uuid.UUID, data: dict[str, Any]) -> ModelType | None:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: uuid.UUID) -> bool:
        """Delete an entity."""
        pass

    @abstractmethod
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities with optional filtering."""
        pass


class AsyncSQLAlchemyRepository(BaseRepository[ModelType]):
    """
    Async SQLAlchemy implementation of the base repository.
    Provides standard CRUD operations for any SQLAlchemy model.
    """

    def __init__(self, db: AsyncSession, model: type[ModelType]):
        """
        Initialize repository with database session and model class.

        Args:
            db: AsyncSession instance
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """
        Get a single entity by its ID.

        Args:
            id: UUID of the entity

        Returns:
            Entity if found, None otherwise
        """
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """
        Get all entities with pagination and optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field-value pairs to filter by

        Returns:
            List of entities
        """
        query = select(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, entity: ModelType) -> ModelType:
        """
        Create a new entity.

        Args:
            entity: Entity instance to create

        Returns:
            Created entity with generated ID
        """
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, id: uuid.UUID, data: dict[str, Any]) -> ModelType | None:
        """
        Update an existing entity.

        Args:
            id: UUID of the entity to update
            data: Dictionary of field-value pairs to update

        Returns:
            Updated entity if found, None otherwise
        """
        entity = await self.get_by_id(id)
        if not entity:
            return None

        for field, value in data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, id: uuid.UUID) -> bool:
        """
        Delete an entity by ID.

        Args:
            id: UUID of the entity to delete

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if not entity:
            return False

        await self.db.delete(entity)
        await self.db.flush()
        return True

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count entities with optional filtering.

        Args:
            filters: Dictionary of field-value pairs to filter by

        Returns:
            Count of matching entities
        """
        query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(self, id: uuid.UUID) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            id: UUID to check

        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def bulk_create(self, entities: list[ModelType]) -> list[ModelType]:
        """
        Create multiple entities in a single transaction.

        Args:
            entities: List of entity instances to create

        Returns:
            List of created entities
        """
        for entity in entities:
            self.db.add(entity)

        await self.db.flush()

        for entity in entities:
            await self.db.refresh(entity)

        return entities

    async def get_by_field(self, field: str, value: Any) -> ModelType | None:
        """
        Get a single entity by a specific field value.

        Args:
            field: Field name to filter by
            value: Value to match

        Returns:
            Entity if found, None otherwise
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} has no field '{field}'")

        query = select(self.model).where(getattr(self.model, field) == value)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_many_by_field(
        self, field: str, value: Any, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """
        Get multiple entities by a specific field value.

        Args:
            field: Field name to filter by
            value: Value to match
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching entities
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} has no field '{field}'")

        query = (
            select(self.model).where(getattr(self.model, field) == value).offset(skip).limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())


class SyncSQLAlchemyRepository[ModelType: BaseModel]:
    """
    Synchronous SQLAlchemy implementation for legacy support.
    Use AsyncSQLAlchemyRepository for new code.
    """

    def __init__(self, db: Session, model: type[ModelType]):
        self.db = db
        self.model = model

    def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        query = self.db.query(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        return query.offset(skip).limit(limit).all()

    def create(self, entity: ModelType) -> ModelType:
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def update(self, id: uuid.UUID, data: dict[str, Any]) -> ModelType | None:
        entity = self.get_by_id(id)
        if not entity:
            return None

        for field, value in data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, id: uuid.UUID) -> bool:
        entity = self.get_by_id(id)
        if not entity:
            return False

        self.db.delete(entity)
        self.db.flush()
        return True
