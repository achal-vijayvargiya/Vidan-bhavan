#!/usr/bin/env python3
"""
Script to create admin users with proper password hashing.
Run this after installing werkzeug: pip install werkzeug
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from app.data_modals import User
from app.database.db_conn_postgresql import DATABASE_URL

def create_admin_user(username, email, password, first_name="Admin", last_name="User"):
    """Create an admin user with proper password hashing"""
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = SessionLocal()
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"ℹ️  User '{username}' already exists")
            return False
        
        # Create admin user with proper password hashing
        admin_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            role='admin',
            is_active=True,
            is_verified=True,
            department='IT',
            position='System Administrator'
        )
        
        db.add(admin_user)
        db.commit()
        
        print(f"✅ Admin user '{username}' created successfully!")
        print(f"👤 Username: {username}")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print("⚠️  Remember to change the password in production!")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Creating admin user with proper password hashing...")
    print("Make sure you have installed werkzeug: pip install werkzeug")
    
    # You can modify these values
    username = "admin"
    email = "admin@vidhanbhavan.com"
    password = "admin123"
    
    if create_admin_user(username, email, password):
        print("\n✅ Admin user created successfully!")
        print("You can now use this user to log into your application.")
    else:
        print("\n❌ Failed to create admin user.")
        print("Make sure:")
        print("1. The users table exists (run create_users_table.py first)")
        print("2. Werkzeug is installed: pip install werkzeug")
        print("3. Your database is running and accessible") 