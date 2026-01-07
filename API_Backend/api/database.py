"""
Database setup with better error handling
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys

# Create database engine
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tradeguard.db")
print(f"📊 Database URL: {DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=True  # Enable SQL logging for debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

def init_db():
    """Initialize database by creating all tables"""
    try:
        from api import models  # Import models here to avoid circular imports
        
        print("🔧 Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Database initialized successfully!")
        print(f"📋 Tables created: {tables}")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_db():
    """Dependency to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_tables():
    """Check which tables exist"""
    inspector = inspect(engine)
    return inspector.get_table_names()