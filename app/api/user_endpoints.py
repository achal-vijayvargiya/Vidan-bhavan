"""
Example API endpoints for user management
This file shows how to integrate the User model with your existing API structure
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.database.db_conn_postgresql import get_db
from app.data_modals import User
from app.utils.auth_utils import (
    create_user, 
    authenticate_user, 
    get_user_by_username,
    update_user_password,
    deactivate_user,
    activate_user
)

router = APIRouter(prefix="/api/users", tags=["users"])

# Pydantic models for request/response
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "user"
    phone_number: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None

from uuid import UUID

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    is_verified: bool
    phone_number: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    profile_image_url: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class UserLoginResponse(BaseModel):
    user: UserResponse
    message: str

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

# API Endpoints

@router.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if username already exists
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        phone_number=user_data.phone_number,
        department=user_data.department,
        position=user_data.position
    )
    
    return user

@router.post("/login", response_model=UserLoginResponse)
def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return user data
    """
    user = authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create a dictionary with string user_id to avoid UUID validation issues
    user_dict = {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "phone_number": user.phone_number,
        "department": user.department,
        "position": user.position,
        "profile_image_url": user.profile_image_url,
        "last_login": user.last_login,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    
    return {
        "user": user_dict,
        "message": "Login successful"
    }

@router.get("/me", response_model=UserResponse)
def get_current_user(username: str, db: Session = Depends(get_db)):
    """
    Get current user information
    """
    user = get_user_by_username(db, username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create a dictionary with string user_id to avoid UUID validation issues
    user_dict = {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "phone_number": user.phone_number,
        "department": user.department,
        "position": user.position,
        "profile_image_url": user.profile_image_url,
        "last_login": user.last_login,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    
    return user_dict

@router.get("/", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Get all users (admin only)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.put("/{user_id}/password")
def update_password(
    user_id: str,
    password_data: PasswordUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user password
    """
    # First verify current password
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    from app.utils.auth_utils import verify_password
    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    success = update_user_password(db, user_id, password_data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    return {"message": "Password updated successfully"}

@router.put("/{user_id}/deactivate")
def deactivate_user_account(user_id: str, db: Session = Depends(get_db)):
    """
    Deactivate a user account (admin only)
    """
    success = deactivate_user(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}

@router.put("/{user_id}/activate")
def activate_user_account(user_id: str, db: Session = Depends(get_db)):
    """
    Activate a user account (admin only)
    """
    success = activate_user(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User activated successfully"}

@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    """
    Get user by ID
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user 