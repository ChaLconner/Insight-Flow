"""
Reusable response helper functions for API routes.
These helpers eliminate duplicate code for response mapping across routers.
"""

from typing import Any


def build_member_summary(member: Any) -> dict[str, Any]:
    """
    Build a member summary dictionary from a ProjectMember object.

    Args:
        member: ProjectMember object with user relationship loaded

    Returns:
        Dictionary with member summary fields
    """
    return {
        "id": str(member.id),
        "user_id": str(member.user_id),
        "name": member.user.name if member.user else "Unknown",
        "email": member.user.email if member.user else "",
        "avatar_url": getattr(member.user, "avatar_url", None) if member.user else None,
        "role": member.role,
    }


def build_member_summaries(members: list[Any]) -> list[dict[str, Any]]:
    """
    Build a list of member summaries from ProjectMember objects.

    Args:
        members: List of ProjectMember objects

    Returns:
        List of member summary dictionaries
    """
    return [build_member_summary(m) for m in members]


def build_user_response(user: Any) -> dict[str, Any]:
    """
    Build a user response dictionary from a User object.

    Args:
        user: User model object

    Returns:
        Dictionary with user fields for API response
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": getattr(user, "avatar_url", None),
        "is_active": user.is_active,
        "role": user.role or "user",
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def build_project_member_response(member: Any) -> dict[str, Any]:
    """
    Build a full project member response dictionary.

    Args:
        member: ProjectMember object with user relationship loaded

    Returns:
        Dictionary with full member response fields
    """
    return {
        "id": member.id,
        "project_id": member.project_id,
        "user_id": member.user_id,
        "role": member.role,
        "joined_at": member.joined_at,
        "user": build_user_response(member.user) if member.user else None,
    }


def build_project_member_responses(members: list[Any]) -> list[dict[str, Any]]:
    """
    Build a list of full project member responses.

    Args:
        members: List of ProjectMember objects

    Returns:
        List of member response dictionaries
    """
    return [build_project_member_response(m) for m in members]


def build_project_response(
    project: Any, details: dict[str, Any] | None = None, members: list[Any] | None = None
) -> dict[str, Any]:
    """
    Build a project response dictionary.

    Args:
        project: Project model object
        details: Optional dict with task_count, completed_tasks, etc.
        members: Optional list of ProjectMember objects

    Returns:
        Dictionary with project response fields
    """
    response = {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "color": getattr(project, "color", None) or "#6366f1",
        "settings": getattr(project, "settings", {}) or {},
        "owner_id": project.owner_id,
        "is_active": project.is_active,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }

    if details:
        response.update(
            {
                "task_count": details.get("task_count", 0),
                "completed_tasks": details.get("completed_tasks", 0),
                "overdue_tasks": details.get("overdue_tasks", 0),
                "recent_activity": details.get("recent_activity"),
                "member_count": details.get("member_count", 0),
            }
        )
    else:
        response.update(
            {
                "task_count": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "member_count": len(members) if members else 0,
            }
        )

    if members:
        response["member_summaries"] = build_member_summaries(members)

    return response


def build_project_with_members_response(
    project: Any, details: dict[str, Any], members: list[Any]
) -> dict[str, Any]:
    """
    Build a full project with members response dictionary.

    Args:
        project: Project model object
        details: Dict with task_count, completed_tasks, etc.
        members: List of ProjectMember objects

    Returns:
        Dictionary with full project + members response fields
    """
    response = build_project_response(project, details, members)
    response["members"] = build_project_member_responses(members)
    return response


def normalize_task_status(status: Any) -> str:
    """Return normalized task status text for API responses and activity logs."""
    status_value = getattr(status, "value", status)
    return str(status_value).lower() if status_value else "todo"


def build_task_response(task: Any, include_relations: bool = True) -> dict[str, Any]:
    """
    Build a task response dictionary.

    Args:
        task: Task model object
        include_relations: Whether to include assignee/creator/project details

    Returns:
        Dictionary with task response fields
    """
    status_val = normalize_task_status(getattr(task, "status", None))
    priority_val = (
        task.priority.value
        if hasattr(task.priority, "value")
        else getattr(task, "priority", "medium")
    )
    type_val = task.type.value if hasattr(task.type, "value") else getattr(task, "type", "task")
    creator_id = getattr(task, "created_by", None) or getattr(task, "creator_id", None)

    response = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": status_val,
        "priority": priority_val,
        "type": type_val,
        "project_id": task.project_id,
        "assignee_id": task.assignee_id,
        "created_by": creator_id,
        "due_date": task.due_date,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }

    if include_relations:
        if hasattr(task, "assignee"):
            response["assignee"] = task.assignee
        if hasattr(task, "creator"):
            response["creator"] = task.creator
        if hasattr(task, "project"):
            response["project"] = task.project
            response["project_name"] = getattr(task.project, "name", None) if task.project else None

    return response


def build_notification_response(notification: Any) -> dict[str, Any]:
    """
    Build a notification response dictionary.
    """
    return {
        "id": str(notification.id),
        "user_id": str(notification.user_id),
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "data": notification.data,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }


__all__ = [
    "build_member_summaries",
    "build_member_summary",
    "build_notification_response",
    "build_project_member_response",
    "build_project_member_responses",
    "build_project_response",
    "build_project_with_members_response",
    "build_task_response",
    "build_user_response",
    "normalize_task_status",
]
