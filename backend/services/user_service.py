"""
User service layer for authentication and user management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from models.user import User
from schemas.user import UserCreate, UserLogin, UserUpdate, UserInvite
from utils.auth import get_password_hash, authenticate_user, verify_password
from utils.validators import validate_password_strength
from utils.logger import logger
import uuid
import time

class UserService:
    """Service class for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with retry logic for connection errors."""
        logger.debug(f"get_user_by_email called with email: {email}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1} to query user by email")
                user = self.db.query(User).filter(User.email == email).first()
                logger.debug(f"Query completed, User found: {user is not None}")
                return user
            except OperationalError as e:
                logger.error(f"OperationalError on attempt {attempt + 1}: {e}")
                if "SSL connection has been closed unexpectedly" in str(e) and attempt < max_retries - 1:
                    # Wait before retrying
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise e
    
    def get_user_by_id(self, user_id) -> Optional[User]:
        """Get user by ID."""
        try:
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            return self.db.query(User).filter(User.id == user_id).first()
        except ValueError:
            # Handle invalid UUID string
            return None
    
    def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        return self.db.query(User).filter(User.google_id == google_id).first()
    
    def get_user_by_github_id(self, github_id: str) -> Optional[User]:
        """Get user by GitHub ID."""
        return self.db.query(User).filter(User.github_id == github_id).first()
    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using the configured hashing method."""
        return get_password_hash(password)
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        try:
            # Create user object
            # Ensure name consistency
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
                github_id=getattr(user_data, 'github_id', None),
                role="user",  # Set default role
                username=user_data.username,
                phone=user_data.phone,
                bio=user_data.bio,
                location=user_data.location,
                website=user_data.website
            )
           
            # Hash password if provided
            # Hash password if provided
            if user_data.password:
                validate_password_strength(user_data.password)
                db_user.hashed_password = get_password_hash(user_data.password)
           
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
           
        except IntegrityError as e:
            self.db.rollback()
            if "email" in str(e):
                raise ValueError("Email already registered")
            elif "google_id" in str(e):
                raise ValueError("Google account already linked")
            elif "username" in str(e):
                raise ValueError("Username already taken")
            else:
                raise ValueError("User creation failed")
    
    def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """Authenticate user with email and password."""
        logger.info(f"authenticate_user called for email: {login_data.email}")
        
        user = self.get_user_by_email(login_data.email)
        if not user:
            logger.warning(f"User not found for email: {login_data.email}")
            return None
            
        if not authenticate_user(user, login_data.password):
            logger.warning(f"Password authentication failed for email: {login_data.email}")
            return None
            
        logger.info(f"Authentication successful for email: {login_data.email}")
        return user

    def update_user(self, user_id: uuid.UUID, user_update: UserUpdate) -> User:
        """Update user profile."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        update_data = user_update.model_dump(exclude_unset=True)
        
        # Handle first_name and last_name updates explicitly
        if 'first_name' in update_data:
            user.first_name = update_data['first_name']
        if 'last_name' in update_data:
            user.last_name = update_data['last_name']
            
        # Update name if first/last changed or if name is explicitly provided
        if 'name' in update_data:
            user.name = update_data['name']
        elif 'first_name' in update_data or 'last_name' in update_data:
            first = update_data.get('first_name', user.first_name or "")
            last = update_data.get('last_name', user.last_name or "")
            user.name = f"{first} {last}".strip()

        for key, value in update_data.items():
            if key not in ['first_name', 'last_name', 'name']: # Already handled
                setattr(user, key, value)

        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            if "username" in str(e):
                raise ValueError("Username already taken")
            raise ValueError("User update failed")

    def delete_user(self, user_id: uuid.UUID) -> bool:
        """Delete a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        try:
            self.db.delete(user)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Cannot delete user - user has associated data")

    def search_users(self, query: str, skip: int = 0, limit: int = 100, role: Optional[str] = None, is_active: Optional[bool] = None) -> List[User]:
        """Search users by email or name with pagination and filters."""
        db_query = self.db.query(User)
        
        if query and len(query.strip()) > 0:
            query = query.strip()
            db_query = db_query.filter(
                (User.email.ilike(f"%{query}%")) | (User.name.ilike(f"%{query}%"))
            )
        
        if role and role != "all":
            db_query = db_query.filter(User.role == role)
            
        if is_active is not None:
            db_query = db_query.filter(User.is_active == is_active)
            
        return db_query.offset(skip).limit(limit).all()
    
    def create_or_update_google_user(self, google_id: str, email: str, name: str, avatar_url: Optional[str] = None) -> User:
        """Create or update user from Google authentication."""
        # Check if user exists by Google ID
        user = self.get_user_by_google_id(google_id)
        if user:
            # Update existing user
            user.email = email
            user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # Check if user exists by email (to merge accounts)
        user = self.get_user_by_email(email)
        if user:
            # Link Google account to existing user
            user.google_id = google_id
            user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # Create new user
        user_data = UserCreate(
            email=email,
            name=name,
            avatar_url=avatar_url,
            google_id=google_id
        )
        return self.create_user(user_data)

    def create_or_update_github_user(self, github_id: str, email: str, name: str, avatar_url: Optional[str] = None) -> User:
        """Create or update user from GitHub authentication."""
        # Check if user exists by GitHub ID
        user = self.get_user_by_github_id(github_id)
        if user:
            # Update existing user
            user.email = email
            user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # Check if user exists by email (to merge accounts)
        user = self.get_user_by_email(email)
        if user:
            # Link GitHub account to existing user
            user.github_id = github_id
            if not user.name:
                user.name = name
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            self.db.commit()
            self.db.refresh(user)
            return user
        
        # Create new user
        user_data = UserCreate(
            email=email,
            name=name,
            avatar_url=avatar_url,
            github_id=github_id
        )
        return self.create_user(user_data)

    def change_password(self, user_id: uuid.UUID, current_password: str, new_password: str) -> bool:
        """Change user password."""
        logger.info(f"Password change request for user ID: {user_id}")
        user = self.get_user_by_id(user_id)
        if not user:
            logger.error(f"User not found for ID: {user_id}")
            raise ValueError("User not found")
        
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            logger.warning(f"Current password verification failed for user: {user.email}")
            raise ValueError("Incorrect current password")
        
        # Update password
        validate_password_strength(new_password)
        user.hashed_password = self.hash_password(new_password)
        logger.info(f"Password updated for user: {user.email}")
        
        try:
            self.db.commit()
            logger.info(f"Password change committed successfully for user: {user.email}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error changing password for user {user.email}: {e}")
            raise ValueError("Failed to change password")
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        try:
            return verify_password(password, hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def invite_user(self, user_invite: UserInvite) -> User:
        """Invite an existing user (update role and activate)."""
        # Check for existing user
        db_user = self.get_user_by_email(user_invite.email)
        if not db_user:
            raise ValueError("User not found. Please ask them to register first.")
            
        # Update user role and status
        db_user.role = user_invite.role or "user"
        db_user.is_active = True
        
        try:
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inviting user: {e}")
            raise ValueError("Failed to invite user")

    def get_user_stats(self) -> dict:
        """Get user statistics."""
        total = self.db.query(User).count()
        active = self.db.query(User).filter(User.is_active == True).count()
        verified = self.db.query(User).filter(User.is_active == True).count() # Assuming active implies verified
        
        admins = self.db.query(User).filter(User.role == "admin").count()
        managers = self.db.query(User).filter(User.role == "manager").count()
        members = self.db.query(User).filter(User.role == "member").count()
        viewers = self.db.query(User).filter(User.role == "viewer").count()
        
        return {
            "total": total,
            "active": active,
            "verified": verified,
            "admins": admins,
            "managers": managers,
            "members": members,
            "viewers": viewers
        }