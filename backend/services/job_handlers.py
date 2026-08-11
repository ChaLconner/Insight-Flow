"""Handlers for durable jobs executed by the dedicated worker process."""

import uuid
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.project import Project, ProjectMember
from models.task import Task
from models.user import User
from services.async_deadline_reminder import run_async_deadline_check
from services.async_notification_trigger_service import AsyncNotificationTriggerService
from services.email_service import EmailService
from services.job_payload_security import decrypt_job_secret
from utils.logger import setup_logger

logger = setup_logger("job_handlers")

EMAIL_JOB_TYPE = "email.send"
NOTIFICATION_JOB_TYPE = "notification.dispatch"
DEADLINE_JOB_TYPE = "deadline.check"


def _uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


async def _send_email(payload: dict[str, Any]) -> None:
    """Send one email and raise on failure so the queue retries it."""
    method = payload.get("method", "send_email")
    if method == "send_email":
        sent = await EmailService.send_email(
            payload["to_email"], payload["subject"], payload["html_content"]
        )
    elif method == "verification":
        sent = await EmailService.send_verification_email(payload["email"], _email_token(payload))
    elif method == "password_reset":
        sent = await EmailService.send_password_reset_email(payload["email"], _email_token(payload))
    elif method == "account_lockout":
        sent = await EmailService.send_account_lockout_notification(
            email=payload["email"],
            locked_until=payload["locked_until"],
            ip_address=payload.get("ip_address"),
            user_agent=payload.get("user_agent"),
        )
    else:
        raise ValueError(f"Unknown email method: {method}")

    if not sent:
        raise RuntimeError(f"Email provider rejected {method} delivery")


def _email_token(payload: dict[str, Any]) -> str:
    """Return a protected token, with compatibility for already queued legacy jobs."""
    protected_token = payload.get("token_encrypted")
    if protected_token:
        return decrypt_job_secret(protected_token)

    # Jobs created before encrypted payloads were introduced may still be in
    # the queue. Keep the compatibility path narrow and do not write it again.
    legacy_token = payload.get("token")
    if isinstance(legacy_token, str) and legacy_token:
        logger.warning("Processing a legacy unprotected email job payload")
        return legacy_token
    raise ValueError("Email job is missing its protected token")


async def _load_task(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.project),
        )
        .where(Task.id == task_id)
    )
    return result.scalars().first()


async def _load_users(db: AsyncSession, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {user.id: user for user in result.scalars().all()}


async def _dispatch_task_assigned(
    db: AsyncSession, payload: dict[str, Any], service: AsyncNotificationTriggerService
) -> None:
    task = await _load_task(db, _uuid(payload["task_id"]))
    users = await _load_users(db, [_uuid(payload["assignee_id"]), _uuid(payload["assigner_id"])])
    if not task or not task.assignee or not task.project:
        logger.info("Skipping task assignment notification for missing task relations")
        return
    assigner = users.get(_uuid(payload["assigner_id"]))
    if assigner:
        await service.notify_task_assigned(
            assignee=task.assignee,
            task_id=task.id,
            task_title=task.title,
            project_id=task.project_id,
            project_name=task.project.name,
            assigner=assigner,
        )


async def _dispatch_task_status_changed(
    db: AsyncSession, payload: dict[str, Any], service: AsyncNotificationTriggerService
) -> None:
    task = await _load_task(db, _uuid(payload["task_id"]))
    changer = (await _load_users(db, [_uuid(payload["changer_id"])])).get(
        _uuid(payload["changer_id"])
    )
    if not task or not changer:
        return
    await service.notify_task_status_changed(
        task_id=task.id,
        task_title=task.title,
        project_id=task.project_id,
        old_status=payload["old_status"],
        new_status=payload["new_status"],
        changer=changer,
        assignee=task.assignee,
        creator=task.creator,
    )
    if payload.get("completed"):
        await service.notify_task_completed(
            task_id=task.id,
            task_title=task.title,
            project_id=task.project_id,
            project_name=task.project.name if task.project else "Unknown Project",
            completer=changer,
            creator=task.creator,
        )


async def _dispatch_project_member_added(
    db: AsyncSession, payload: dict[str, Any], service: AsyncNotificationTriggerService
) -> None:
    member_id = _uuid(payload["member_id"])
    inviter_id = _uuid(payload["inviter_id"])
    users = await _load_users(db, [member_id, inviter_id])
    member = users.get(member_id)
    inviter = users.get(inviter_id)
    if member and inviter:
        await service.notify_project_member_added(
            new_member=member,
            project_id=_uuid(payload["project_id"]),
            project_name=payload["project_name"],
            role=payload["role"],
            inviter=inviter,
        )


async def _dispatch_project_member_removed(
    db: AsyncSession, payload: dict[str, Any], service: AsyncNotificationTriggerService
) -> None:
    member_id = _uuid(payload["member_id"])
    remover_id = _uuid(payload["remover_id"])
    users = await _load_users(db, [member_id, remover_id])
    member = users.get(member_id)
    remover = users.get(remover_id)
    if member and remover:
        await service.notify_project_member_removed(
            removed_member=member,
            project_id=_uuid(payload["project_id"]),
            project_name=payload["project_name"],
            remover=remover,
        )


async def _dispatch_mention(
    db: AsyncSession, payload: dict[str, Any], service: AsyncNotificationTriggerService
) -> None:
    mentioned_user_id = _uuid(payload["mentioned_user_id"])
    project_id = _uuid(payload["project_id"]) if payload.get("project_id") else None
    if project_id:
        membership = await db.execute(
            select(Project.id)
            .outerjoin(
                ProjectMember,
                and_(
                    ProjectMember.project_id == Project.id,
                    ProjectMember.user_id == mentioned_user_id,
                ),
            )
            .where(
                Project.id == project_id,
                or_(
                    Project.owner_id == mentioned_user_id,
                    ProjectMember.user_id.is_not(None),
                ),
            )
        )
        if membership.scalar_one_or_none() is None:
            logger.info("Skipping mention for a non-member recipient")
            return

    actor_id = _uuid(payload["actor_id"])
    users = await _load_users(db, [mentioned_user_id, actor_id])
    mentioned_user = users.get(mentioned_user_id)
    actor = users.get(actor_id)
    if mentioned_user and mentioned_user.is_active and actor and actor.is_active:
        await service.notify_mention(
            mentioned_user=mentioned_user,
            actor=actor,
            message=payload["message"],
            project_id=project_id,
            task_id=_uuid(payload["task_id"]) if payload.get("task_id") else None,
        )


async def _dispatch_notification(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Dispatch notification intent after reloading fresh ORM state."""
    event = payload["event"]
    service = AsyncNotificationTriggerService(db)

    if event == "task_assigned":
        await _dispatch_task_assigned(db, payload, service)
        return

    if event == "task_status_changed":
        await _dispatch_task_status_changed(db, payload, service)
        return

    if event == "project_member_added":
        await _dispatch_project_member_added(db, payload, service)
        return

    if event == "project_member_removed":
        await _dispatch_project_member_removed(db, payload, service)
        return

    if event == "mention":
        await _dispatch_mention(db, payload, service)
        return

    raise ValueError(f"Unknown notification event: {event}")


async def handle_job(db: AsyncSession, job_type: str, payload: dict[str, Any]) -> None:
    """Run one job type; exceptions are intentionally propagated for retries."""
    if job_type == EMAIL_JOB_TYPE:
        await _send_email(payload)
    elif job_type == NOTIFICATION_JOB_TYPE:
        await _dispatch_notification(db, payload)
    elif job_type == DEADLINE_JOB_TYPE:
        await run_async_deadline_check(db)
    else:
        raise ValueError(f"Unknown background job type: {job_type}")
