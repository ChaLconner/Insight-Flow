"""
Security Audit Logger for sensitive operations.
Provides structured logging for security events like login attempts,
permission changes, and suspicious activities.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

SecurityLogModel: Any = None

# Import models securely
try:
    from models.security_log import SecurityLog as _SecurityLogModel
except ImportError:
    SECURITY_LOG_MODEL_AVAILABLE = False
else:
    SecurityLogModel = _SecurityLogModel
    SECURITY_LOG_MODEL_AVAILABLE = True


# Setup dedicated security audit logger
AUDIT_LOG_FILE = os.getenv("SECURITY_AUDIT_LOG_FILE", "logs/security_audit.log")
AUDIT_LOG_LEVEL = os.getenv("SECURITY_AUDIT_LOG_LEVEL", "INFO")


class AuditEventType(StrEnum):
    """Types of security events to audit."""

    # Authentication events
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    TOKEN_REFRESH_FAILED = "TOKEN_REFRESH_FAILED"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST"
    PASSWORD_RESET_SUCCESS = "PASSWORD_RESET_SUCCESS"
    PASSWORD_RESET_FAILED = "PASSWORD_RESET_FAILED"

    # OAuth events
    OAUTH_LOGIN_SUCCESS = "OAUTH_LOGIN_SUCCESS"
    OAUTH_LOGIN_FAILED = "OAUTH_LOGIN_FAILED"
    OAUTH_ACCOUNT_LINKED = "OAUTH_ACCOUNT_LINKED"

    # Authorization events
    ACCESS_DENIED = "ACCESS_DENIED"
    PERMISSION_ESCALATION = "PERMISSION_ESCALATION"
    ROLE_CHANGE = "ROLE_CHANGE"

    # Account events
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    ACCOUNT_UPDATED = "ACCOUNT_UPDATED"
    ACCOUNT_DELETED = "ACCOUNT_DELETED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_UNLOCKED = "ACCOUNT_UNLOCKED"

    # Resource events
    SENSITIVE_DATA_ACCESS = "SENSITIVE_DATA_ACCESS"
    BULK_DATA_EXPORT = "BULK_DATA_EXPORT"

    # Security threats
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CSRF_VALIDATION_FAILED = "CSRF_VALIDATION_FAILED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    BRUTE_FORCE_DETECTED = "BRUTE_FORCE_DETECTED"

    # Admin operations
    ADMIN_ACTION = "ADMIN_ACTION"
    CONFIG_CHANGE = "CONFIG_CHANGE"


@dataclass
class AuditEvent:
    """Structured audit event."""

    event_type: AuditEventType
    timestamp: str
    user_id: str | None = None
    user_email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    status: str = "success"  # success, failure, warning
    details: dict[str, Any] | None = None
    severity: str = "info"  # info, warning, critical

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class SecurityAuditLogger:
    """
    Security audit logger for tracking sensitive operations.
    Logs to both file and standard logger for integration with log aggregation.
    """

    _instance: Optional["SecurityAuditLogger"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the audit logger."""
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(getattr(logging, AUDIT_LOG_LEVEL.upper()))

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(AUDIT_LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # File handler for audit logs
        if not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            try:
                file_handler = logging.FileHandler(AUDIT_LOG_FILE)
                file_handler.setFormatter(
                    logging.Formatter("%(message)s")  # JSON format, no additional formatting
                )
                self.logger.addHandler(file_handler)
            except Exception as e:
                # Fallback to console if file logging fails
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter("%(message)s"))
                self.logger.addHandler(console_handler)
                self.logger.warning(f"Could not create audit log file: {e}")

        # Prevent propagation to root logger
        self.logger.propagate = False

    def log_event(self, event: AuditEvent, db: AsyncSession | None = None):
        """Log an audit event."""
        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "critical": logging.CRITICAL,
        }.get(event.severity, logging.INFO)

        self.logger.log(log_level, event.to_json())

        # Log to Database if session is provided
        if db and SECURITY_LOG_MODEL_AVAILABLE and SecurityLogModel is not None:
            try:
                db_chat = SecurityLogModel(
                    event_type=event.event_type.value,
                    severity=event.severity,
                    user_id=event.user_id,
                    ip_address=event.ip_address,
                    user_agent=event.user_agent[:255] if event.user_agent else None,
                    request_path=event.details.get("endpoint") if event.details else None,
                    details=event.details,
                    timestamp=datetime.fromisoformat(event.timestamp),
                )
                db.add(db_chat)
            except Exception as e:
                self.logger.error(f"Failed to log to database: {e}")

    def log_login_success(
        self,
        user_id: str,
        user_email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        auth_method: str = "password",
        db: AsyncSession | None = None,
    ):
        """Log successful login."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.LOGIN_SUCCESS,
                timestamp=datetime.now(UTC).isoformat(),
                user_id=user_id,
                user_email=self._mask_email(user_email),
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                action="login",
                status="success",
                details={"auth_method": auth_method},
            ),
            db=db,
        )

    def log_login_failed(
        self,
        user_email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        reason: str = "invalid_credentials",
        db: AsyncSession | None = None,
    ):
        """Log failed login attempt."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.LOGIN_FAILED,
                timestamp=datetime.now(UTC).isoformat(),
                user_email=self._mask_email(user_email),
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                action="login",
                status="failure",
                severity="warning",
                details={"reason": reason},
            ),
            db=db,
        )

    def log_logout(
        self,
        user_id: str,
        user_email: str,
        ip_address: str | None = None,
        request_id: str | None = None,
        db: AsyncSession | None = None,
    ):
        """Log user logout."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.LOGOUT,
                timestamp=datetime.now(UTC).isoformat(),
                user_id=user_id,
                user_email=self._mask_email(user_email),
                ip_address=ip_address,
                request_id=request_id,
                action="logout",
                status="success",
            ),
            db=db,
        )

    def log_access_denied(
        self,
        user_id: str | None,
        resource_type: str,
        resource_id: str,
        ip_address: str | None = None,
        request_id: str | None = None,
        reason: str = "insufficient_permissions",
        db: AsyncSession | None = None,
    ):
        """Log access denied event."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.ACCESS_DENIED,
                timestamp=datetime.now(UTC).isoformat(),
                user_id=user_id,
                ip_address=ip_address,
                request_id=request_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action="access",
                status="failure",
                severity="warning",
                details={"reason": reason},
            ),
            db=db,
        )

    def log_password_change(
        self,
        user_id: str,
        user_email: str,
        ip_address: str | None = None,
        request_id: str | None = None,
        db: AsyncSession | None = None,
    ):
        """Log password change."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.PASSWORD_CHANGE,
                timestamp=datetime.now(UTC).isoformat(),
                user_id=user_id,
                user_email=self._mask_email(user_email),
                ip_address=ip_address,
                request_id=request_id,
                action="password_change",
                status="success",
                severity="info",
            ),
            db=db,
        )

    def log_rate_limit_exceeded(
        self,
        ip_address: str,
        endpoint: str,
        request_id: str | None = None,
        db: AsyncSession | None = None,
    ):
        """Log rate limit exceeded event."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                timestamp=datetime.now(UTC).isoformat(),
                ip_address=ip_address,
                request_id=request_id,
                resource_type="endpoint",
                resource_id=endpoint,
                action="rate_limit",
                status="failure",
                severity="warning",
                details={"endpoint": endpoint},
            ),
            db=db,
        )

    def log_csrf_failed(
        self,
        ip_address: str,
        endpoint: str,
        request_id: str | None = None,
        db: AsyncSession | None = None,
    ):
        """Log CSRF validation failure."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.CSRF_VALIDATION_FAILED,
                timestamp=datetime.now(UTC).isoformat(),
                ip_address=ip_address,
                request_id=request_id,
                resource_type="endpoint",
                resource_id=endpoint,
                action="csrf_validation",
                status="failure",
                severity="warning",
            ),
            db=db,
        )

    def log_suspicious_activity(
        self,
        ip_address: str,
        description: str,
        user_id: str | None = None,
        request_id: str | None = None,
        db: AsyncSession | None = None,
    ):
        """Log suspicious activity."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                timestamp=datetime.now(UTC).isoformat(),
                user_id=user_id,
                ip_address=ip_address,
                request_id=request_id,
                action="suspicious_activity",
                status="warning",
                severity="critical",
                details={"description": description},
            ),
            db=db,
        )

    def log_account_created(
        self,
        user_id: str,
        user_email: str,
        ip_address: str | None = None,
        request_id: str | None = None,
        registration_method: str = "email",
        db: AsyncSession | None = None,
    ):
        """Log account creation."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.ACCOUNT_CREATED,
                timestamp=datetime.now(UTC).isoformat(),
                user_id=user_id,
                user_email=self._mask_email(user_email),
                ip_address=ip_address,
                request_id=request_id,
                action="account_create",
                status="success",
                details={"registration_method": registration_method},
            ),
            db=db,
        )

    def log_role_change(
        self,
        user_id: str,
        target_user_id: str,
        old_role: str,
        new_role: str,
        resource_type: str = "global",
        resource_id: str | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
        db: AsyncSession | None = None,
    ):
        """Log role change."""
        self.log_event(
            AuditEvent(
                event_type=AuditEventType.ROLE_CHANGE,
                timestamp=datetime.now(UTC).isoformat(),
                user_id=user_id,
                ip_address=ip_address,
                request_id=request_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action="role_change",
                status="success",
                severity="warning",
                details={
                    "target_user_id": target_user_id,
                    "old_role": old_role,
                    "new_role": new_role,
                },
            ),
            db=db,
        )

    @staticmethod
    def _mask_email(email: str | None) -> str | None:
        """Mask email for privacy in logs."""
        if not email or "@" not in email:
            return email
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"


# Global singleton instance
security_audit = SecurityAuditLogger()
