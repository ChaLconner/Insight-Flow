"""
Async Task service layer for task management.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import re
import uuid
from datetime import UTC
from typing import Any

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.project import MemberRole, Project, ProjectMember
from models.task import Task, TaskPriority, TaskStatus, TaskType
from models.user import User
from schemas.task import TaskAssign, TaskCreate, TaskStatusUpdate, TaskUpdate
from utils.logger import logger


def escape_like_pattern(pattern: str) -> str:
    """
    Escape special characters in SQL LIKE patterns to prevent wildcard injection.

    Escapes: % (any chars), _ (single char), \\ (escape char)
    """
    return re.sub(r"([%_\\])", r"\\\1", pattern)


async def _invalidate_dashboard_cache_after_mutation(user_id: uuid.UUID | None = None) -> None:
    try:
        from services.async_analytics_service import invalidate_analytics_cache
        from services.async_dashboard_service import invalidate_dashboard_cache

        await invalidate_dashboard_cache(user_id)
        await invalidate_analytics_cache(user_id)
    except Exception as e:
        logger.error(f"Failed to invalidate dashboard/analytics cache: {e}")


class AsyncTaskService:
    """Async Service class for task operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_task_by_id(self, task_id: uuid.UUID) -> Task | None:
        """Get task by ID."""
        result = await self.db.execute(select(Task).filter(Task.id == task_id))
        return result.scalars().first()

    async def get_task_with_details(self, task_id: uuid.UUID) -> Task | None:
        """Get task by ID with all relationships eagerly loaded."""
        result = await self.db.execute(
            select(Task)
            .options(
                selectinload(Task.assignee), selectinload(Task.creator), selectinload(Task.project)
            )
            .filter(Task.id == task_id)
        )
        return result.scalars().first()

    async def get_tasks(
        self,
        skip: int = 0,
        limit: int = 100,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        """Get tasks with pagination and optional filters."""
        query = select(Task).options(
            selectinload(Task.assignee), selectinload(Task.creator), selectinload(Task.project)
        )

        if project_id:
            query = query.filter(Task.project_id == project_id)
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)
        if status:
            query = query.filter(Task.status == status)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _is_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of the project."""
        # Check if owner
        project_result = await self.db.execute(select(Project).filter(Project.id == project_id))
        project = project_result.scalars().first()
        if project and project.owner_id == user_id:
            return True

        # Check if member
        member_result = await self.db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
            )
        )
        return member_result.scalars().first() is not None

    async def _is_project_admin(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is admin or owner of the project."""
        # Check if owner
        project_result = await self.db.execute(select(Project).filter(Project.id == project_id))
        project = project_result.scalars().first()
        if project and project.owner_id == user_id:
            return True

        # Check if admin member
        member_result = await self.db.execute(
            select(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.role.in_([MemberRole.ADMIN.value, MemberRole.OWNER.value]),
            )
        )
        return member_result.scalars().first() is not None

    async def create_task(self, task_data: TaskCreate, created_by: uuid.UUID) -> Task:
        """Create a new task."""
        logger.info(f"Creating task with data: {task_data}, created_by: {created_by}")

        # Check if project exists
        project_result = await self.db.execute(
            select(Project).filter(Project.id == task_data.project_id)
        )
        project = project_result.scalars().first()
        if not project:
            raise ValueError("Project not found")

        # Permission Check: User must be a project member to create tasks
        if not await self._is_project_member(task_data.project_id, created_by):
            logger.warning(
                f"User {created_by} attempted to create task in project {task_data.project_id} without membership"
            )
            raise ValueError("Not authorized to create tasks in this project")

        # Check if assignee exists (if provided)
        assignee = None
        if task_data.assignee_id:
            assignee_result = await self.db.execute(
                select(User).filter(User.id == task_data.assignee_id)
            )
            assignee = assignee_result.scalars().first()
            if not assignee:
                raise ValueError("Assignee not found")

        try:
            # Handle status
            task_status = TaskStatus.from_value(task_data.status, default=TaskStatus.TODO)

            # Handle priority
            task_priority = TaskPriority.from_value(task_data.priority, default=TaskPriority.MEDIUM)

            # Handle type
            task_type = TaskType.from_value(task_data.type, default=TaskType.FEATURE)

            db_task = Task(
                title=task_data.title,
                description=task_data.description,
                status=task_status,
                priority=task_priority,
                type=task_type,
                project_id=task_data.project_id,
                assignee_id=task_data.assignee_id,
                created_by=created_by,
                due_date=task_data.due_date,
            )

            self.db.add(db_task)
            await self.db.commit()
            await self.db.refresh(db_task)
            await _invalidate_dashboard_cache_after_mutation()

            # Log activity asynchronously
            try:
                from services.async_task_history_service import AsyncTaskHistoryService

                history_service = AsyncTaskHistoryService(self.db)
                await history_service.log_task_created(db_task, created_by)
                if task_data.assignee_id:
                    await history_service.log_task_assigned(
                        db_task, task_data.assignee_id, created_by
                    )
            except Exception as e:
                logger.error(f"Failed to log task creation activity: {e}")

            return db_task

        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Task creation failed")
        except Exception as e:
            await self.db.rollback()
            raise ValueError(f"Task creation failed: {e!s}")

    async def _check_task_permission(
        self, task: Task, user_id: uuid.UUID, allow_assignee: bool = False
    ) -> None:
        """
        Check if user has permission to modify task.
        Raises ValueError if unauthorized.
        """
        is_authorized = False

        # Creator is always authorized
        if (
            task.created_by == user_id
            or (allow_assignee and task.assignee_id == user_id)
            or await self._is_project_admin(task.project_id, user_id)
        ):
            is_authorized = True

        if not is_authorized:
            logger.warning(f"User {user_id} unauthorized for task {task.id}")
            raise ValueError("Not authorized to perform this action on this task")

    async def _get_authorized_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID, allow_assignee: bool = False
    ) -> Task:
        task = await self.get_task_by_id(task_id)
        if not task:
            raise ValueError("Task not found")

        await self._check_task_permission(task, user_id, allow_assignee=allow_assignee)
        return task

    def _build_task_list_query(
        self, filters: list[Any], search: str | None = None, status: str | None = None
    ) -> tuple[Any, list[Any]]:
        query = (
            select(Task)
            .options(
                selectinload(Task.assignee), selectinload(Task.creator), selectinload(Task.project)
            )
            .filter(*filters)
            .order_by(Task.created_at.desc())
        )

        if search:
            escaped_search = escape_like_pattern(search)
            search_term = f"%{escaped_search}%"
            search_filter = or_(
                Task.title.ilike(search_term, escape="\\"),
                Task.description.ilike(search_term, escape="\\"),
            )
            filters.append(search_filter)
            query = query.filter(search_filter)

        if status and status.lower() != "all":
            status_filter = Task.status == status.lower()
            filters.append(status_filter)
            query = query.filter(status_filter)

        return query, filters

    async def update_task(  # noqa: PLR0912, PLR0915
        self, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID
    ) -> Task:
        """Update task information."""
        task = await self._get_authorized_task(task_id, user_id, allow_assignee=True)

        # Check if assignee exists (if provided)
        if task_data.assignee_id:
            assignee_result = await self.db.execute(
                select(User).filter(User.id == task_data.assignee_id)
            )
            if not assignee_result.scalars().first():
                raise ValueError("Assignee not found")

        old_values: dict[str, Any] = {}
        new_values: dict[str, Any] = {}
        old_assignee_id = task.assignee_id
        old_status = task.status

        # Update fields
        if task_data.title is not None and task_data.title != task.title:
            old_values["title"] = task.title
            new_values["title"] = task_data.title
            task.title = task_data.title

        if task_data.description is not None and task_data.description != task.description:
            old_values["description"] = task.description
            new_values["description"] = task_data.description
            task.description = task_data.description

        if task_data.status is not None:
            new_status = TaskStatus.from_value(task_data.status)
            if new_status and new_status != task.status:
                old_values["status"] = task.status.value
                new_values["status"] = new_status.value
                task.status = new_status

        if task_data.priority is not None:
            new_priority = TaskPriority.from_value(task_data.priority)
            if new_priority and new_priority != task.priority:
                old_values["priority"] = task.priority.value
                new_values["priority"] = new_priority.value
                task.priority = new_priority

        if task_data.type is not None:
            new_type = TaskType.from_value(task_data.type)
            if new_type and new_type != task.type:
                old_values["type"] = task.type.value
                new_values["type"] = new_type.value
                task.type = new_type

        if task_data.assignee_id is not None and task_data.assignee_id != task.assignee_id:
            task.assignee_id = task_data.assignee_id
            if old_assignee_id:
                old_values["assignee_id"] = str(old_assignee_id)
            new_values["assignee_id"] = str(task_data.assignee_id)

        if task_data.due_date is not None and task_data.due_date != task.due_date:
            old_values["due_date"] = task.due_date.isoformat() if task.due_date else None
            new_values["due_date"] = task_data.due_date.isoformat() if task_data.due_date else None
            task.due_date = task_data.due_date

        try:
            await self.db.commit()
            await self.db.refresh(task)
            await _invalidate_dashboard_cache_after_mutation()

            # Log activity
            try:
                from services.async_task_history_service import AsyncTaskHistoryService

                history_service = AsyncTaskHistoryService(self.db)

                if old_values or new_values:
                    await history_service.log_task_updated(task, user_id, old_values, new_values)

                if task_data.assignee_id and task_data.assignee_id != old_assignee_id:
                    await history_service.log_task_assigned(task, task_data.assignee_id, user_id)

                if task.status == TaskStatus.DONE and old_status != TaskStatus.DONE:
                    await history_service.log_task_completed(task, user_id)
            except Exception as e:
                logger.error(f"Failed to log task update activity: {e}")

            return task
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Task update failed")

    async def delete_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a task."""
        task = await self._get_authorized_task(task_id, user_id)

        # Log before delete
        try:
            from services.async_task_history_service import AsyncTaskHistoryService

            history_service = AsyncTaskHistoryService(self.db)
            await history_service.log_task_deleted(task, user_id)
        except Exception as e:
            logger.error(f"Failed to log task deletion activity: {e}")

        try:
            # Note: delete() is synchronous in SQLAlchemy 2.0 AsyncSession (it stages the deletion)
            await self.db.delete(task)
            await self.db.commit()
            await _invalidate_dashboard_cache_after_mutation()
            return True
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Task deletion failed")

    async def update_task_status(
        self, task_id: uuid.UUID, status_update: TaskStatusUpdate, user_id: uuid.UUID
    ) -> Task:
        """Update task status."""
        task = await self._get_authorized_task(task_id, user_id, allow_assignee=True)

        old_status = task.status

        try:
            new_status = TaskStatus.from_value(status_update.status)
            if not new_status:
                raise ValueError("Invalid task status")
            task.status = new_status

            await self.db.commit()
            await self.db.refresh(task)
            await _invalidate_dashboard_cache_after_mutation()

            # Log activity
            if old_status != task.status:
                try:
                    from services.async_task_history_service import AsyncTaskHistoryService

                    history_service = AsyncTaskHistoryService(self.db)

                    if task.status == TaskStatus.DONE:
                        await history_service.log_task_completed(task, user_id)
                    else:
                        await history_service.log_task_updated(
                            task,
                            user_id,
                            {"status": old_status.value},
                            {"status": task.status.value},
                        )
                except Exception as e:
                    logger.error(f"Failed to log status update activity: {e}")

            return task
        except ValueError as e:
            raise e
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Task status update failed")

    async def assign_task(
        self, task_id: uuid.UUID, assign_data: TaskAssign, user_id: uuid.UUID
    ) -> Task:
        """Assign task to a user."""
        task = await self._get_authorized_task(task_id, user_id)

        # Check assignee exists
        assignee_result = await self.db.execute(
            select(User).filter(User.id == assign_data.assignee_id)
        )
        assignee = assignee_result.scalars().first()
        if not assignee:
            raise ValueError("Assignee not found")

        try:
            task.assignee_id = assign_data.assignee_id
            await self.db.commit()
            await self.db.refresh(task)
            await _invalidate_dashboard_cache_after_mutation()

            # Log activity
            try:
                from services.async_task_history_service import AsyncTaskHistoryService

                history_service = AsyncTaskHistoryService(self.db)
                await history_service.log_task_assigned(task, assign_data.assignee_id, user_id)
            except Exception as e:
                logger.error(f"Failed to log assignment activity: {e}")

            return task
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Task assignment failed")

    async def get_user_tasks(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Task], int]:
        """
        Get tasks assigned to or created by a user with optional filtering.
        Returns a tuple of (tasks, total_count).
        """
        filters = [or_(Task.assignee_id == user_id, Task.created_by == user_id)]
        query, filters = self._build_task_list_query(filters, search, status)

        # Count total
        count_query = select(func.count(Task.id)).filter(*filters)
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Order and paginate
        query = query.order_by(desc(Task.updated_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total_count

    async def get_project_tasks(
        self,
        project_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str | None = None,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Task], int]:
        """
        Get tasks for a specific project with optional sorting and filtering.
        Returns (tasks, total_count).
        """
        filters = [Task.project_id == project_id]
        query, filters = self._build_task_list_query(filters, search, status)

        # Apply sorting
        if sort_by:
            sort_field_map = {
                "created_at": Task.created_at,
                "updated_at": Task.updated_at,
                "title": Task.title,
                "due_date": Task.due_date,
                "status": Task.status,
                "priority": Task.priority,
                "type": Task.type,
            }

            if sort_by in sort_field_map:
                sort_field = sort_field_map[sort_by]
                if sort_order and sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(asc(sort_field))
        else:
            query = query.order_by(desc(Task.updated_at))

        # Count total
        count_query = select(func.count(Task.id)).filter(*filters)
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total_count

    async def get_tasks_due_soon(
        self, user_id: uuid.UUID, days: int = 7, limit: int = 10
    ) -> list[Task]:
        """Get tasks due within specified days for a user."""
        from datetime import datetime, timedelta

        now = datetime.now(UTC)
        due_date_threshold = now + timedelta(days=days)

        query = (
            select(Task)
            .options(selectinload(Task.project))
            .filter(
                Task.assignee_id == user_id,
                Task.status != TaskStatus.DONE,
                Task.due_date.isnot(None),
                Task.due_date <= due_date_threshold,
                Task.due_date >= now.date(),
            )
            .order_by(asc(Task.due_date))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_overdue_tasks(self, user_id: uuid.UUID, limit: int = 20) -> list[Task]:
        """Get overdue tasks for a user."""
        from datetime import datetime

        now = datetime.now(UTC).date()

        query = (
            select(Task)
            .options(selectinload(Task.project))
            .filter(
                Task.assignee_id == user_id,
                Task.status != TaskStatus.DONE,
                Task.due_date.isnot(None),
                Task.due_date < now,
            )
            .order_by(asc(Task.due_date))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_task_stats_for_user(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Get task statistics for a user."""
        from sqlalchemy import String, case, cast

        stats_query = select(
            func.count(Task.id).label("total"),
            func.sum(case((cast(Task.status, String) == TaskStatus.DONE.value, 1), else_=0)).label(
                "completed"
            ),
            func.sum(
                case((cast(Task.status, String) == TaskStatus.IN_PROGRESS.value, 1), else_=0)
            ).label("in_progress"),
            func.sum(case((cast(Task.status, String) == TaskStatus.TODO.value, 1), else_=0)).label(
                "todo"
            ),
        ).filter(or_(Task.assignee_id == user_id, Task.created_by == user_id))

        result = await self.db.execute(stats_query)
        row = result.first()

        if not row:
            return {"total": 0, "completed": 0, "in_progress": 0, "todo": 0, "completion_rate": 0}

        total = row[0] or 0
        completed = row[1] or 0
        in_progress = row[2] or 0
        todo = row[3] or 0
        completion_rate = round(completed / total * 100) if total > 0 else 0

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "todo": todo,
            "completion_rate": completion_rate,
        }
