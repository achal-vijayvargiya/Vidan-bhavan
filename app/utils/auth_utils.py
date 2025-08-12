"""
Authentication utilities for user management
"""

try:
    from werkzeug.security import generate_password_hash, check_password_hash
    WERKZEUG_AVAILABLE = True
except ImportError:
    WERKZEUG_AVAILABLE = False
    print("Warning: werkzeug not installed. Password hashing will use simple methods.")
from datetime import datetime
from typing import Optional
from app.data_modals import User
from sqlalchemy.orm import Session
from app.logging.logger import Logger
logger = Logger()

def hash_password(password: str) -> str:
    """
    Hash a password using werkzeug's security functions or simple hash
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    if WERKZEUG_AVAILABLE:
        return generate_password_hash(password)
    else:
        # Simple hash for development - NOT for production!
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password (str): Plain text password to verify
        password_hash (str): Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    if WERKZEUG_AVAILABLE:
        return check_password_hash(password_hash, password)
    else:
        # Simple verification for development - NOT for production!
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == password_hash

def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str = 'user',
    **kwargs
) -> User:
    """
    Create a new user in the database
    
    Args:
        db (Session): Database session
        username (str): Unique username
        email (str): Unique email address
        password (str): Plain text password (will be hashed)
        first_name (str): User's first name
        last_name (str): User's last name
        role (str): User role (default: 'user')
        **kwargs: Additional user fields
        
    Returns:
        User: Created user object
    """
    # Hash the password
    password_hash = hash_password(password)
    
    # Create user object
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
        role=role,
        **kwargs
    )
    
    # Add to database
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password
    
    Args:
        db (Session): Database session
        username (str): Username to authenticate
        password (str): Plain text password
        
    Returns:
        Optional[User]: User object if authentication successful, None otherwise
    """
    # Find user by username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    # Check if user is active
    if not user.is_active:
        return None
    
    # Verify password
    if not verify_password(password, user.password_hash):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    logger.info(f"User '{user.username}' logged in at {user.last_login}")    
    return user

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Get user by username
    
    Args:
        db (Session): Database session
        username (str): Username to search for
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get user by email
    
    Args:
        db (Session): Database session
        email (str): Email to search for
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()

def update_user_password(db: Session, user_id: str, new_password: str) -> bool:
    """
    Update user's password
    
    Args:
        db (Session): Database session
        user_id (str): User ID
        new_password (str): New plain text password
        
    Returns:
        bool: True if successful, False otherwise
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return False
    
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return True

def deactivate_user(db: Session, user_id: str) -> bool:
    """
    Deactivate a user account
    
    Args:
        db (Session): Database session
        user_id (str): User ID to deactivate
        
    Returns:
        bool: True if successful, False otherwise
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return False
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return True

def activate_user(db: Session, user_id: str) -> bool:
    """
    Activate a user account
    
    Args:
        db (Session): Database session
        user_id (str): User ID to activate
        
    Returns:
        bool: True if successful, False otherwise
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return False
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return True 