"""
Initialize database tables for Deriv integration
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from api.database import engine, Base
from api.modelss.integration_models import DerivConnection, DerivTrade, SyncLog, WebhookEvent

print("🔧 Creating integration database tables...")
try:
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Integration tables created successfully!")
    
    # List tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"📋 All tables: {tables}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()