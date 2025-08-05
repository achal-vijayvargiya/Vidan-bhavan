import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Get database URL from environment variable with fallback
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://postgres:postgres@localhost:5432/vidhan-pg")

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Create a configured "Session" class
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    """
    Dependency to get a SQLAlchemy session.
    Usage:
        db = get_db()
        try:
            # use db
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 