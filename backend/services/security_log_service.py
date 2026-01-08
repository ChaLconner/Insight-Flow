import logging
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.security_log import SecurityLog

logger = logging.getLogger("security_logger")


class SecurityLogService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: str,
        severity: str = "info",
        details: dict[str, Any] | None = None,
        user_id: str | None = None,
        request: Request | None = None,
        ip_address: str | None = None,
    ):
        """
        Log a security event to the database.

        Args:
            db: Database session
            event_type: Type of event (e.g. 'csp_violation', 'login_failed')
            severity: 'info', 'warning', 'error', 'critical'
            details: JSON dict with extra info
            user_id: User ID if known
            request: FastAPI request object (to extract IP/UA/Path)
            ip_address: Explicit IP override
        """
        try:
            # Extract context from request if provided
            req_path = None
            req_method = None
            user_agent = None

            if request:
                req_path = str(request.url.path)
                req_method = request.method
                user_agent = request.headers.get("user-agent")
                if not ip_address:
                    ip_address = request.client.host if request.client else None

            log_entry = SecurityLog(
                event_type=event_type,
                severity=severity,
                details=details,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent[:255] if user_agent else None,
                request_path=req_path[:255] if req_path else None,
                request_method=req_method,
            )

            db.add(log_entry)
            # We might want to fire_and_forget this in high load,
            # but for now commit is safer
            await db.commit()

        except Exception as e:
            logger.error(f"Failed to write security log: {e}")
            # Don't raise, we don't want to break the app flow just for logging
