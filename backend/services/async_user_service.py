"""
Async User service layer for authentication and user management.
Refactored for SQLAlchemy 2.0+ Async operations with Enhanced Security.
"""

import asyncio
import hashlib
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth_audit import AuthAudit, AuthStatus
from models.payment import Subscription, SubscriptionPlan, SubscriptionStatus
from models.user import User
from models.user_settings import UserSettings
from schemas.user import UserCreate, UserInvite, UserLogin, UserSettingsUpdate, UserUpdate
from services.email_service import EmailService
from utils.auth import get_password_hash, verify_password
from utils.logger import logger, mask_email, mask_token, mask_user_id
from utils.validators import validate_password_strength

# Thread pool for CPU-bound operations (password hashing)
_password_executor = ThreadPoolExecutor(max_workers=4)


def escape_like_pattern(pattern: str) -> str:
    """
    Escape special characters in SQL LIKE patterns to prevent wildcard injection.
    """
    return re.sub(r"([%_\\])", r"\\\1", pattern)


class AsyncUserService:
    """Async Service class for user operations with A+ Security features."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _hash_token(self, token: str) -> str:
        """Create SHA256 hash of the token."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def get_user_by_google_id(self, google_id: str) -> User | None:
        """Get user by Google ID."""
        result = await self.db.execute(select(User).filter(User.google_id == google_id))
        return result.scalars().first()

    async def get_user_by_github_id(self, github_id: str) -> User | None:
        """Get user by GitHub ID."""
        result = await self.db.execute(select(User).filter(User.github_id == github_id))
        return result.scalars().first()

    async def hash_password(self, password: str) -> str:
        """Hash a password using run_in_executor to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_password_executor, get_password_hash, password)

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with secure verification token."""
        try:
            name = user_data.name
            if not name and (user_data.first_name or user_data.last_name):
                name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip()

            db_user = User(
                email=user_data.email,
                name=name,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                avatar_url=user_data.avatar_url,
                google_id=user_data.google_id,
                github_id=getattr(user_data, "github_id", None),
                role="member",
                username=user_data.username,
                phone=user_data.phone,
                bio=user_data.bio,
                location=user_data.location,
                website=user_data.website,
            )

            if user_data.password:
                validate_password_strength(user_data.password)
                db_user.hashed_password = await self.hash_password(user_data.password)

            # Verification Logic (A+ Security)
            # Create raw token (sent via email)
            raw_token = str(uuid.uuid4())
            # Store hashed token in DB
            db_user.verification_token = self._hash_token(raw_token)
            # Set expiration (24 hours)
            db_user.verification_token_expires_at = datetime.now(UTC) + timedelta(hours=24)
            db_user.is_verified = False
            db_user.is_active = True

            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)

            # Handle Trial Subscription
            if user_data.plan and user_data.plan.lower() in ["starter", "pro", "enterprise"]:
                try:
                    trial_end = datetime.now(UTC) + timedelta(days=14)
                    new_sub = Subscription(
                        user_id=db_user.id,
                        plan=SubscriptionPlan(user_data.plan.lower()),
                        status=SubscriptionStatus.TRIALING,
                        current_period_start=datetime.now(UTC).isoformat(),
                        current_period_end=trial_end.isoformat(),
                        cancel_at_period_end=False,
                    )
                    self.db.add(new_sub)
                    await self.db.commit()
                    logger.info(
                        f"Created trial subscription ({user_data.plan}) for user {db_user.email}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create trial subscription for user {db_user.email}: {e}"
                    )

            # Send verification email with raw token (not hashed)
            await EmailService.send_verification_email(db_user.email, raw_token)

            return db_user

        except IntegrityError as e:
            await self.db.rollback()
            if "email" in str(e):
                raise ValueError("Email already registered")
            elif "google_id" in str(e):
                raise ValueError("Google account already linked")
            elif "username" in str(e):
                raise ValueError("Username already taken")
            else:
                raise ValueError("User creation failed")

    async def verify_email(self, token: str) -> bool:
        """Verify user email with secure token check."""
        # Hash input token to match stored hash
        hashed_token = self._hash_token(token)

        result = await self.db.execute(select(User).filter(User.verification_token == hashed_token))
        user = result.scalars().first()

        if not user:
            # Try to match legacy unhashed tokens (backward compatibility)
            # In case old tokens are pending
            legacy_result = await self.db.execute(
                select(User).filter(User.verification_token == token)
            )
            user = legacy_result.scalars().first()

        if not user:
            logger.warning(f"Verification failed: Invalid token {mask_token(token)}")
            return False

        # Check expiration
        if user.verification_token_expires_at and user.verification_token_expires_at < datetime.now(
            UTC
        ):
            logger.warning(f"Verification failed: Token expired for user {mask_email(user.email)}")
            return False

        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        await self.db.commit()

        logger.info(f"Email verified successfully for {mask_email(user.email)}")
        return True

    async def resend_verification_email(self, email: str) -> bool:
        """Resend verification email with new token."""
        user = await self.get_user_by_email(email)
        if not user:
            # Don't reveal user existence
            return True

        if user.is_verified:
            logger.info(
                f"Resend verification requested for already verified user: {mask_email(email)}"
            )
            return True

        # Generate new token
        raw_token = str(uuid.uuid4())
        user.verification_token = self._hash_token(raw_token)
        user.verification_token_expires_at = datetime.now(UTC) + timedelta(hours=24)

        await self.db.commit()

        # Send email
        await EmailService.send_verification_email(email, raw_token)
        logger.info(f"Verification email resent to {mask_email(email)}")
        return True

    async def log_auth_attempt(
        self,
        email: str,
        status: AuthStatus,
        ip_address: str | None,
        user_agent: str | None,
        user_id: uuid.UUID | None = None,
    ):
        """Log authentication attempt."""
        try:
            audit = AuthAudit(
                user_id=user_id,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status.value,
                attempt_at=datetime.now(UTC),
            )
            self.db.add(audit)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log auth attempt: {e}")
            await self.db.rollback()

    async def authenticate_user(
        self,
        login_data: UserLogin,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User | None:
        """Authenticate user with email and password, handling lockout and audit logs."""
        logger.info(f"authenticate_user called for email: {mask_email(login_data.email)}")

        user = await self.get_user_by_email(login_data.email)

        # 1. Check if user exists
        if not user:
            logger.warning(f"User not found for email: {mask_email(login_data.email)}")
            await self.log_auth_attempt(
                login_data.email, AuthStatus.FAILURE, ip_address, user_agent
            )
            return None

        # 2. Check if locked out
        if user.locked_until and user.locked_until > datetime.now(UTC):
            logger.warning(f"Account locked for user: {mask_email(user.email)}")
            await self.log_auth_attempt(
                login_data.email, AuthStatus.LOCKED, ip_address, user_agent, user.id
            )
            raise ValueError(f"Account locked. Try again after {user.locked_until}")

        # 3. Verify Password
        if not user.hashed_password or not await self.verify_password(
            login_data.password, user.hashed_password
        ):
            logger.warning(
                f"Password authentication failed for email: {mask_email(login_data.email)}"
            )

            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            # Lock if >= 5 attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
                logger.warning(f"Locking account for user: {mask_email(user.email)}")

                # A+ Security: Send account lockout notification email
                try:
                    from utils.background_tasks import fire_and_forget

                    async def send_lockout_notification():
                        await EmailService.send_account_lockout_notification(
                            email=user.email,
                            locked_until=user.locked_until,
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                    fire_and_forget(send_lockout_notification())
                except Exception as e:
                    logger.debug(f"Lockout notification skipped: {e}")

            await self.db.commit()

            await self.log_auth_attempt(
                login_data.email, AuthStatus.FAILURE, ip_address, user_agent, user.id
            )
            return None

        # 4. Success
        if (user.failed_login_attempts or 0) > 0 or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None
            await self.db.commit()

        logger.info(f"Authentication successful for email: {mask_email(login_data.email)}")
        await self.log_auth_attempt(
            login_data.email, AuthStatus.SUCCESS, ip_address, user_agent, user.id
        )
        return user

    async def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash using run_in_executor to avoid blocking."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _password_executor, verify_password, password, hashed_password
            )
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> bool:
        """Change user password."""
        logger.info(f"Password change request for user ID: {mask_user_id(str(user_id))}")
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.error(f"User not found for ID: {mask_user_id(str(user_id))}")
            raise ValueError("User not found")

        if not verify_password(current_password, user.hashed_password or ""):
            logger.warning(
                f"Current password verification failed for user: {mask_email(user.email)}"
            )
            raise ValueError("Incorrect current password")

        validate_password_strength(new_password)
        user.hashed_password = await self.hash_password(new_password)
        logger.info(f"Password updated for user: {mask_email(user.email)}")

        try:
            await self.db.commit()
            logger.info(
                f"Password change committed successfully for user: {mask_email(user.email)}"
            )
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error changing password for user {mask_email(user.email)}: {e}")
            raise ValueError("Failed to change password")

    async def create_or_update_google_user(
        self, google_id: str, email: str, name: str, avatar_url: str | None = None
    ) -> User:
        """Create or update user from Google authentication."""
        user = await self.get_user_by_google_id(google_id)
        if user:
            user.email = email
            user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            await self.db.commit()
            await self.db.refresh(user)
            return user

        user = await self.get_user_by_email(email)
        if user:
            user.google_id = google_id
            user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            await self.db.commit()
            await self.db.refresh(user)
            return user

        user_data = UserCreate(email=email, name=name, avatar_url=avatar_url, google_id=google_id)
        return await self.create_user(user_data)

    async def create_or_update_github_user(
        self, github_id: str, email: str, name: str, avatar_url: str | None = None
    ) -> User:
        """Create or update user from GitHub authentication."""
        user = await self.get_user_by_github_id(github_id)
        if user:
            user.email = email
            user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            await self.db.commit()
            await self.db.refresh(user)
            return user

        user = await self.get_user_by_email(email)
        if user:
            user.github_id = github_id
            if not user.name:
                user.name = name
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            await self.db.commit()
            await self.db.refresh(user)
            return user

        user_data = UserCreate(email=email, name=name, avatar_url=avatar_url, github_id=github_id)
        return await self.create_user(user_data)

    async def update_last_login(self, user_id: uuid.UUID | str) -> None:
        """Update last login timestamp without loading the full user row."""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            await self.db.execute(
                update(User).where(User.id == user_id).values(last_login_at=datetime.now(UTC))
            )
            await self.db.commit()
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid user ID for last login update: {e}")
        except Exception as e:
            logger.error(f"Failed to update last login time: {e}")
            await self.db.rollback()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email with retry logic for connection errors."""
        logger.debug(f"get_user_by_email called with email: {mask_email(email)}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await self.db.execute(select(User).filter(User.email == email))
                user = result.scalars().first()
                return user
            except TimeoutError as e:
                logger.error(f"Database timeout on attempt {attempt + 1}: {e}")
                await self.db.rollback()
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise e
            except OperationalError as e:
                logger.error(f"OperationalError on attempt {attempt + 1}: {e}")
                await self.db.rollback()
                if (
                    "SSL connection has been closed unexpectedly" in str(e)
                    and attempt < max_retries - 1
                ):
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise e
        return None

    async def get_user_by_id(self, user_id) -> User | None:
        """Get user by ID."""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            result = await self.db.execute(select(User).filter(User.id == user_id))
            return result.scalars().first()
        except ValueError:
            return None

    async def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get users with pagination."""
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_user(self, user_id: uuid.UUID, user_update: UserUpdate) -> User:
        """Update user profile."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        update_data = user_update.model_dump(exclude_unset=True)

        if "first_name" in update_data:
            user.first_name = update_data["first_name"]
        if "last_name" in update_data:
            user.last_name = update_data["last_name"]

        if "name" in update_data:
            user.name = update_data["name"]
        elif "first_name" in update_data or "last_name" in update_data:
            first = update_data.get("first_name", user.first_name or "")
            last = update_data.get("last_name", user.last_name or "")
            user.name = f"{first} {last}".strip()

        for key, value in update_data.items():
            if key not in ["first_name", "last_name", "name"]:
                setattr(user, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(user)

            # Invalidate dashboard/analytics cache if user role or status changed
            # (affects team statistics displayed on dashboard)
            if "role" in update_data or "is_active" in update_data:
                try:
                    from services.async_analytics_service import invalidate_analytics_cache
                    from services.async_dashboard_service import invalidate_dashboard_cache

                    invalidate_dashboard_cache()
                    invalidate_analytics_cache()
                except Exception as e:
                    logger.error(f"Failed to invalidate cache after user update: {e}")

            return user
        except IntegrityError as e:
            await self.db.rollback()
            if "username" in str(e):
                raise ValueError("Username already taken")
            raise ValueError("User update failed")

    async def invite_user(self, user_invite: UserInvite) -> User:
        """Invite an existing user (update role and activate)."""
        db_user = await self.get_user_by_email(user_invite.email)
        if not db_user:
            raise ValueError("User not found. Please ask them to register first.")

        db_user.role = user_invite.role or "member"
        db_user.is_active = True

        try:
            await self.db.commit()
            await self.db.refresh(db_user)
            return db_user
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error inviting user: {e}")
            raise ValueError("Failed to invite user")

    async def get_user_stats(self) -> dict:
        """Get user statistics using a single optimized query."""
        from sqlalchemy import case

        query = select(
            func.count(User.id).label("total"),
            func.sum(case((User.is_active == True, 1), else_=0)).label("active"),
            func.sum(case((User.role == "admin", 1), else_=0)).label("admins"),
            func.sum(case((User.role == "manager", 1), else_=0)).label("managers"),
            func.sum(case((or_(User.role == "member", User.role == "user"), 1), else_=0)).label(
                "members"
            ),
            func.sum(case((User.role == "viewer", 1), else_=0)).label("viewers"),
        )

        result = await self.db.execute(query)
        stats = result.first()

        if not stats:
            return {
                "total": 0,
                "active": 0,
                "verified": 0,
                "admins": 0,
                "managers": 0,
                "members": 0,
                "viewers": 0,
            }

        return {
            "total": stats.total or 0,
            "active": stats.active or 0,
            "verified": stats.active or 0,
            "admins": stats.admins or 0,
            "managers": stats.managers or 0,
            "members": stats.members or 0,
            "viewers": stats.viewers or 0,
        }

    async def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        """Search users."""
        stmt = select(User)

        if query and len(query.strip()) > 0:
            escaped_query = escape_like_pattern(query.strip())
            stmt = stmt.filter(
                or_(
                    User.email.ilike(f"%{escaped_query}%"),
                    User.name.ilike(f"%{escaped_query}%"),
                )
            )

        if role and role != "all":
            stmt = stmt.filter(User.role == role)

        if is_active is not None:
            stmt = stmt.filter(User.is_active == is_active)

        result = await self.db.execute(stmt.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_or_create_settings(self, user_id: uuid.UUID) -> UserSettings:
        """Get or create user settings."""
        result = await self.db.execute(select(UserSettings).filter(UserSettings.user_id == user_id))
        settings = result.scalars().first()

        if not settings:
            settings = UserSettings(user_id=user_id)
            self.db.add(settings)
            try:
                await self.db.commit()
                await self.db.refresh(settings)
            except IntegrityError:
                await self.db.rollback()
                result = await self.db.execute(
                    select(UserSettings).filter(UserSettings.user_id == user_id)
                )
                settings = result.scalars().first()

        if not settings:
            raise ValueError("Could not retrieve user settings")
        return settings

    async def update_settings(
        self, user_id: uuid.UUID, settings_data: UserSettingsUpdate
    ) -> UserSettings:
        """
        Update user settings using direct UPDATE for performance.
        Falls back to create if settings don't exist.
        """
        update_data = settings_data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_or_create_settings(user_id)

        try:
            # Try direct update first (faster, less locking)
            stmt = (
                update(UserSettings)
                .where(UserSettings.user_id == user_id)
                .values(**update_data)
                .returning(UserSettings)
            )
            result = await self.db.execute(stmt)
            settings = result.scalars().first()

            if settings:
                await self.db.commit()
                return settings

            # If no row updated, it doesn't exist -> Create it
            settings = await self.get_or_create_settings(user_id)

            # Apply updates to the newly created settings
            for key, value in update_data.items():
                setattr(settings, key, value)

            await self.db.commit()
            return settings

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating settings for user {user_id}: {e}")
            raise ValueError("Failed to update settings")
