"""
Async User service layer for authentication and user management.
Refactored for SQLAlchemy 2.0+ Async operations.
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from models.auth_audit import AuthAudit, AuthStatus
from models.user import User
from models.user_settings import UserSettings
from schemas.user import UserCreate, UserInvite, UserLogin, UserSettingsUpdate, UserUpdate
from services.email_service import EmailService
from utils.auth import authenticate_user, get_password_hash, verify_password
from utils.logger import logger, mask_email, mask_user_id
from utils.validators import validate_password_strength

# Thread pool for CPU-bound operations (password hashing)
_password_executor = ThreadPoolExecutor(max_workers=4)


class AsyncUserService:
    """Async Service class for user operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

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
        """Create a new user."""
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

            # Verification Logic
            verification_token = str(uuid.uuid4())
            db_user.verification_token = verification_token
            db_user.is_verified = False
            # Assuming is_active means 'not banned'. Using is_verified for email check.
            db_user.is_active = True

            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)

            # Send verification email in background (fire and forget for now, or await)
            # Since create_user is async, we can await it.
            await EmailService.send_verification_email(db_user.email, verification_token)

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
            # Rollback to ensure session is clean and usable for subsequent operations
            await self.db.rollback()
            # Don't fail the request if logging fails

    async def authenticate_user(
        self, login_data: UserLogin, ip_address: str | None = None, user_agent: str | None = None
    ) -> User | None:
        """Authenticate user with email and password, handling lockout and audit logs."""
        logger.info(f"authenticate_user called for email: {mask_email(login_data.email)}")

        user = await self.get_user_by_email(login_data.email)

        # 1. Check if user exists
        if not user:
            logger.warning(f"User not found for email: {mask_email(login_data.email)}")
            # Log failure (user not found)
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
        if not authenticate_user(user, login_data.password):
            logger.warning(
                f"Password authentication failed for email: {mask_email(login_data.email)}"
            )

            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            # Lock if > 5 attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
                logger.warning(f"Locking account for user: {mask_email(user.email)}")

            await self.db.commit()

            await self.log_auth_attempt(
                login_data.email, AuthStatus.FAILURE, ip_address, user_agent, user.id
            )
            return None

        # 4. Success
        # Reset failed attempts on success
        if (user.failed_login_attempts or 0) > 0 or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None
            await self.db.commit()

        logger.info(f"Authentication successful for email: {mask_email(login_data.email)}")
        await self.log_auth_attempt(
            login_data.email, AuthStatus.SUCCESS, ip_address, user_agent, user.id
        )
        return user

    async def verify_email(self, token: str) -> bool:
        """Verify user email with token."""
        result = await self.db.execute(select(User).filter(User.verification_token == token))
        user = result.scalars().first()

        if not user:
            return False

        user.is_verified = True
        user.verification_token = None  # Clear token
        await self.db.commit()
        return True

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

        # Verify current password
        if not verify_password(current_password, user.hashed_password or ""):
            logger.warning(
                f"Current password verification failed for user: {mask_email(user.email)}"
            )
            raise ValueError("Incorrect current password")

        # Update password
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

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update last login timestamp."""
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(UTC)
            try:
                await self.db.commit()
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
            except OperationalError as e:
                logger.error(f"OperationalError on attempt {attempt + 1}: {e}")
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

        # Logic mirroring Sync service name handling
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
            "verified": stats.active or 0,  # Same as active in original logic
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
            query = query.strip()
            # ilike equivalent for asyncpg/sqlite
            stmt = stmt.filter(or_(User.email.ilike(f"%{query}%"), User.name.ilike(f"%{query}%")))

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
                # Retry fetch if race condition occurred
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
        """Update user settings."""
        settings = await self.get_or_create_settings(user_id)

        update_data = settings_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(settings, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(settings)
            return settings
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating settings for user {user_id}: {e}")
            raise ValueError("Failed to update settings")
