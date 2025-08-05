#!/usr/bin/env python3
"""
Script to create the users table in the database.
Run this script to add the users table to your existing database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from app.data_modals import Base, User
from app.database.db_conn_postgresql import DATABASE_URL

def create_users_table():
    """Create the users table in the database"""
    try:
        # Use the database URL from your existing configuration
        engine = create_engine(DATABASE_URL)
        
        # Create the users table
        User.__table__.create(engine, checkfirst=True)
        
        print("✅ Users table created successfully!")
        print("📋 Table structure:")
        print("   - user_id (UUID, Primary Key)")
        print("   - username (String, Unique, Indexed)")
        print("   - email (String, Unique, Indexed)")
        print("   - password_hash (String)")
        print("   - first_name (String)")
        print("   - last_name (String)")
        print("   - role (String, Default: 'user')")
        print("   - is_active (Boolean, Default: True)")
        print("   - is_verified (Boolean, Default: False)")
        print("   - phone_number (String, Optional)")
        print("   - department (String, Optional)")
        print("   - position (String, Optional)")
        print("   - profile_image_url (String, Optional)")
        print("   - bio (Text, Optional)")
        print("   - last_login (DateTime, Optional)")
        print("   - created_at (DateTime, Auto)")
        print("   - updated_at (DateTime, Auto)")
        print("   - created_by (UUID, Optional)")
        print("   - updated_by (UUID, Optional)")
        
    except Exception as e:
        print(f"❌ Error creating users table: {e}")
        return False
    
    return True

def create_sample_admin_user():
    """Create a sample admin user for testing"""
    try:
        from sqlalchemy.orm import sessionmaker
        
        # Try to import werkzeug for proper password hashing
        try:
            from werkzeug.security import generate_password_hash
            WERKZEUG_AVAILABLE = True
        except ImportError:
            WERKZEUG_AVAILABLE = False
            print("⚠️  Warning: werkzeug not installed. Using simple hash.")
        
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = SessionLocal()
        
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.username == 'admin').first()
        if existing_admin:
            print("ℹ️  Admin user already exists")
            return True
        
        # Create password hash
        password = 'admin123'
        if WERKZEUG_AVAILABLE:
            password_hash = generate_password_hash(password)
            print("✅ Using secure password hashing with werkzeug")
        else:
            # Simple hash for development - NOT for production!
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            print("⚠️  Using simple hash (install werkzeug for production)")
        
        # Create sample admin user with proper password hash
        admin_user = User(
            username='admin',
            email='admin@vidhanbhavan.com',
            password_hash=password_hash,
            first_name='System',
            last_name='Administrator',
            role='admin',
            is_active=True,
            is_verified=True,
            department='IT',
            position='System Administrator'
        )
        
        db.add(admin_user)
        db.commit()
        
        print("✅ Sample admin user created!")
        print("👤 Username: admin")
        print("🔑 Password: admin123")
        print("🔐 Password hash created successfully")
        print("⚠️  Remember to change the password in production!")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample admin user: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Creating users table...")
    if create_users_table():
        print("\n👤 Creating sample admin user...")
        if create_sample_admin_user():
            print("\n✅ Setup complete! You can now use the User model in your application.")
            print("\n💡 Next steps:")
            print("1. Start your FastAPI server: python -m uvicorn app.api.api_file:app --host 0.0.0.0 --port 8000 --reload")
            print("2. Test the API: python test_login_api.py")
            print("3. Use credentials: admin / admin123")
        else:
            print("\n❌ Failed to create admin user. Check the error messages above.")
    else:
        print("\n❌ Setup failed. Please check your database connection.") 