"""
User service layer for authentication and user management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.user import User
from schemas.user import UserCreate, UserLogin, UserUpdate
from utils.auth import get_password_hash, authenticate_user
import uuid

class UserService:
    """Service class for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        return self.db.query(User).filter(User.google_id == google_id).first()
    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        try:
            # Create user object
            db_user = User(
                email=user_data.email,
                name=user_data.name,
                avatar_url=user_data.avatar_url,
                google_id=user_data.google_id
            )
            
            # Hash password if provided
            if user_data.password:
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
            else:
                raise ValueError("User creation failed")
    
    def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(login_data.email)
        if not user:
            return None
        if not authenticate_user(user, login_data.password):
            return None
        return user
    
    def update_user(self, user_id: uuid.UUID, user_data: UserUpdate) -> User:
        """Update user information."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Update fields if provided
        if user_data.name is not None:
            user.name = user_data.name
        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
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