"""
FastAPI Dependencies
Simple dependencies without authentication.
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils_backup.logging_system import RedshiftLogger

# Initialize logger
logger = RedshiftLogger()

async def get_system_info():
    """
    Get basic system information
    """
    try:
        return {
            "status": "operational",
            "mode": "open_access",
            "authentication": False,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.log_error(f"System info failed: {e}")
        return {
            "status": "error",
            "mode": "unknown",
            "authentication": False,
            "version": "unknown"
        }

def no_auth_required():
    """
    Placeholder for endpoints that previously required auth
    """
    return {
        "user": "anonymous",
        "role": "open_access",
        "authenticated": False
    }