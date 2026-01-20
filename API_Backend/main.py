"""
FastAPI app with database - FIXED VERSION
"""
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# Add api directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

# Import database FIRST to create tables
from api.database import init_db, engine, Base
from api import models  # This imports all models

# Import routers
from api.routers import analyze, risk, reports, users, dashboard, alerts, integrations

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database - THIS MUST HAPPEN
    print("🚀 Starting TradeGuard API...")
    
    # IMPORTANT: Force create all tables
    print("📊 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
    
    yield
    
    # Shutdown
    print("👋 Shutting down TradeGuard API")

# Initialize FastAPI app
app = FastAPI(
    title="TradeGuard AI API",
    description="API for trading risk analysis and educational insights",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyze.router, prefix="/api/analyze", tags=["Analysis"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk Assessment"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Predictive Alerts"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])

# Health check endpoints
@app.get("/")
async def root():
    return {
        "message": "TradeGuard AI API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Create tables immediately when module loads (backup)
# This ensures tables exist even if lifespan doesn't run properly
print("🔧 Ensuring database tables exist...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables verified/created")
except Exception as e:
    print(f"❌ Error creating tables: {e}")

# Run the app
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )