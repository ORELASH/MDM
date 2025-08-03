"""
FastAPI Main Application
Simple REST API server for RedshiftManager without authentication.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import uvicorn

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
import json

# Initialize logger (simple fallback)
try:
    from utils_backup.logging_system import RedshiftLogger
    logger = RedshiftLogger()
except:
    import logging
    logger = logging.getLogger(__name__)

# Pydantic models for API
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class SystemInfo(BaseModel):
    status: str
    mode: str
    authentication: bool
    version: str

# Create FastAPI app
app = FastAPI(
    title="RedshiftManager API",
    description="Simple REST API for Amazon Redshift Management - Open Access",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit default
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# API Routes

@app.get("/", response_model=APIResponse)
async def root():
    """
    API root endpoint - health check
    """
    return APIResponse(
        success=True,
        message="RedshiftManager API is running (Open Access Mode)",
        data={
            "version": "1.0.0",
            "status": "healthy",
            "mode": "open_access",
            "authentication": False,
            "endpoints": [
                "/docs",
                "/health",
                "/system/info",
                "/system/status"
            ]
        }
    )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "mode": "open_access"
    }

@app.get("/system/info", response_model=SystemInfo)
async def get_system_info():
    """
    Get basic system information
    """
    return SystemInfo(
        status="operational",
        mode="open_access",
        authentication=False,
        version="1.0.0"
    )

@app.get("/system/status")
async def get_system_status():
    """
    Get system status and metrics
    """
    try:
        status_data = {
            "api_status": "running",
            "mode": "open_access",
            "authentication_enabled": False,
            "uptime": "running",
            "version": "1.0.0",
            "endpoints_available": 4
        }
        
        return APIResponse(
            success=True,
            message="System status retrieved (Open Access Mode)",
            data=status_data
        )
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Custom HTTP exception handler
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    General exception handler
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event
    """
    print("🚀 RedshiftManager API Server Started (Open Access Mode)")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔄 Alternative Docs: http://localhost:8000/redoc")
    print("🔓 Authentication: Disabled")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event
    """
    print("⏹️ RedshiftManager API Server Stopped")

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )