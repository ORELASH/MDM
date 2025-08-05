#!/usr/bin/env python3
"""
Module Management API Router
Real module management endpoints - no mock data
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.module_manager import ModuleManager
from core.logging_system import RedshiftManagerLogger

# Initialize router and logger
router = APIRouter(prefix="/modules", tags=["modules"])
logger = RedshiftManagerLogger()

# Pydantic models
class ModuleResponse(BaseModel):
    name: str
    version: str
    module_type: str
    status: str
    description: Optional[str] = None
    author: Optional[str] = None
    dependencies: List[str] = []
    installed_at: Optional[str] = None
    updated_at: Optional[str] = None

class ModuleInstallRequest(BaseModel):
    module_name: str

class ModuleConfigRequest(BaseModel):
    module_name: str
    config_key: str
    config_value: Any
    data_type: str = "string"

class ModuleStatusRequest(BaseModel):
    module_name: str
    status: str

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

def get_module_manager():
    """Dependency to get ModuleManager instance"""
    try:
        return ModuleManager()
    except Exception as e:
        logger.error(f"Failed to initialize ModuleManager: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize module system")

@router.get("/", response_model=APIResponse, summary="List all available modules")
async def list_modules(
    manager: ModuleManager = Depends(get_module_manager),
    installed_only: bool = Query(False, description="Return only installed modules")
):
    """
    Get list of all available modules or only installed modules
    """
    try:
        if installed_only:
            modules = manager.get_installed_modules()
            logger.info(f"Retrieved {len(modules)} installed modules")
        else:
            discovered = manager.discover_modules()
            installed = manager.get_installed_modules()
            
            # Combine discovered and installed, marking installation status
            modules = []
            installed_names = {m['name'] for m in installed}
            
            for module in discovered:
                module['is_installed'] = module['name'] in installed_names
                modules.append(module)
            
            # Add any installed modules not found in discovery
            for module in installed:
                if module['name'] not in {m['name'] for m in discovered}:
                    module['is_installed'] = True
                    module['is_loadable'] = False  # Not discoverable
                    modules.append(module)
            
            logger.info(f"Retrieved {len(modules)} total modules ({len(installed)} installed)")
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(modules)} modules",
            data=modules
        )
        
    except Exception as e:
        logger.error(f"Failed to list modules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/installed", response_model=APIResponse, summary="Get installed modules")
async def get_installed_modules(manager: ModuleManager = Depends(get_module_manager)):
    """
    Get all installed modules with their status and configuration
    """
    try:
        modules = manager.get_installed_modules()
        
        # Enrich with additional status information
        for module in modules:
            try:
                # Get detailed status
                status = manager.get_module_status(module['name'])
                if status.get('exists'):
                    module['is_loadable'] = status.get('is_loadable', False)
                    
                # Get dependencies status
                deps = manager.get_module_dependencies(module['name'])
                if deps['success']:
                    module['dependency_status'] = deps.get('dependency_status', {})
                    module['all_dependencies_available'] = deps.get('all_available', True)
                    
            except Exception as e:
                logger.warning(f"Failed to get extended info for module {module['name']}: {e}")
        
        logger.info(f"Retrieved {len(modules)} installed modules with status")
        return APIResponse(
            success=True,
            message=f"Retrieved {len(modules)} installed modules",
            data=modules
        )
        
    except Exception as e:
        logger.error(f"Failed to get installed modules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/discovered", response_model=APIResponse, summary="Get discovered modules")
async def get_discovered_modules(manager: ModuleManager = Depends(get_module_manager)):
    """
    Get all modules discovered in the modules directory
    """
    try:
        modules = manager.discover_modules()
        logger.info(f"Discovered {len(modules)} modules")
        
        return APIResponse(
            success=True,
            message=f"Discovered {len(modules)} modules",
            data=modules
        )
        
    except Exception as e:
        logger.error(f"Failed to discover modules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/install", response_model=APIResponse, summary="Install a module")
async def install_module(
    request: ModuleInstallRequest,
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Install a discovered module
    """
    try:
        result = manager.install_module(request.module_name)
        
        if result['success']:
            logger.info(f"Successfully installed module: {request.module_name}")
            
            # Get module info after installation
            module_info = manager.get_module_status(request.module_name)
            
            return APIResponse(
                success=True,
                message=result['message'],
                data=module_info if module_info.get('exists') else None
            )
        else:
            logger.warning(f"Failed to install module {request.module_name}: {result['error']}")
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing module {request.module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/uninstall/{module_name}", response_model=APIResponse, summary="Uninstall a module")
async def uninstall_module(
    module_name: str,
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Uninstall an installed module
    """
    try:
        result = manager.uninstall_module(module_name)
        
        if result['success']:
            logger.info(f"Successfully uninstalled module: {module_name}")
            return APIResponse(
                success=True,
                message=result['message']
            )
        else:
            logger.warning(f"Failed to uninstall module {module_name}: {result['error']}")
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{module_name}/status", response_model=APIResponse, summary="Get module status")
async def get_module_status(
    module_name: str,
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Get detailed status information for a specific module
    """
    try:
        status = manager.get_module_status(module_name)
        
        if not status.get('exists'):
            raise HTTPException(status_code=404, detail=f"Module {module_name} not found")
        
        # Get dependencies information
        deps = manager.get_module_dependencies(module_name)
        if deps['success']:
            status['dependencies_info'] = deps
        
        logger.info(f"Retrieved status for module: {module_name}")
        return APIResponse(
            success=True,
            message=f"Status for module {module_name}",
            data=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{module_name}/status", response_model=APIResponse, summary="Update module status")
async def update_module_status(
    module_name: str,
    request: ModuleStatusRequest,
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Update module status (active, disabled, error)
    """
    try:
        if request.status not in ['active', 'disabled', 'error']:
            raise HTTPException(status_code=400, detail="Status must be 'active', 'disabled', or 'error'")
        
        result = manager.update_module_status(module_name, request.status)
        
        if result['success']:
            logger.info(f"Updated module {module_name} status to {request.status}")
            return APIResponse(
                success=True,
                message=result['message']
            )
        else:
            logger.warning(f"Failed to update module {module_name} status: {result['error']}")
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating status for module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{module_name}/config", response_model=APIResponse, summary="Get module configuration")
async def get_module_config(
    module_name: str,
    config_key: Optional[str] = Query(None, description="Specific configuration key"),
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Get module configuration - all configs or specific key
    """
    try:
        result = manager.get_module_config(module_name, config_key)
        
        if result['success']:
            logger.info(f"Retrieved configuration for module: {module_name}")
            return APIResponse(
                success=True,
                message=f"Configuration for module {module_name}",
                data=result.get('config') if config_key else result.get('configs', {})
            )
        else:
            logger.warning(f"Failed to get config for module {module_name}: {result['error']}")
            raise HTTPException(status_code=404, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config for module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{module_name}/config", response_model=APIResponse, summary="Set module configuration")
async def set_module_config(
    module_name: str,
    request: ModuleConfigRequest,
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Set module configuration value
    """
    try:
        result = manager.set_module_config(
            module_name,
            request.config_key,
            request.config_value,
            request.data_type
        )
        
        if result['success']:
            logger.info(f"Set configuration {request.config_key} for module {module_name}")
            return APIResponse(
                success=True,
                message=result['message']
            )
        else:
            logger.warning(f"Failed to set config for module {module_name}: {result['error']}")
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting config for module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{module_name}/dependencies", response_model=APIResponse, summary="Get module dependencies")
async def get_module_dependencies(
    module_name: str,
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Get module dependency information and status
    """
    try:
        result = manager.get_module_dependencies(module_name)
        
        if result['success']:
            logger.info(f"Retrieved dependencies for module: {module_name}")
            return APIResponse(
                success=True,
                message=f"Dependencies for module {module_name}",
                data=result
            )
        else:
            logger.warning(f"Failed to get dependencies for module {module_name}: {result['error']}")
            raise HTTPException(status_code=404, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dependencies for module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{module_name}/load", response_model=APIResponse, summary="Load module")
async def load_module(
    module_name: str,
    manager: ModuleManager = Depends(get_module_manager)
):
    """
    Dynamically load a module
    """
    try:
        result = manager.load_module(module_name)
        
        if result['success']:
            logger.info(f"Successfully loaded module: {module_name}")
            return APIResponse(
                success=True,
                message=result['message']
            )
        else:
            logger.warning(f"Failed to load module {module_name}: {result['error']}")
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/stats", response_model=APIResponse, summary="Get module system statistics")
async def get_system_stats(manager: ModuleManager = Depends(get_module_manager)):
    """
    Get overall module system statistics
    """
    try:
        installed = manager.get_installed_modules()
        discovered = manager.discover_modules()
        
        stats = {
            'total_discovered': len(discovered),
            'total_installed': len(installed),
            'active_modules': len([m for m in installed if m['status'] == 'active']),
            'disabled_modules': len([m for m in installed if m['status'] == 'disabled']),
            'error_modules': len([m for m in installed if m['status'] == 'error']),
            'loadable_modules': len([m for m in discovered if m.get('is_loadable', False)]),
            'modules_directory': str(manager.modules_dir),
            'database_path': manager.db_path,
            'database_connected': True  # If we got here, DB is working
        }
        
        logger.info("Retrieved module system statistics")
        return APIResponse(
            success=True,
            message="Module system statistics",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/system/refresh", response_model=APIResponse, summary="Refresh module discovery")
async def refresh_modules(manager: ModuleManager = Depends(get_module_manager)):
    """
    Refresh module discovery - scan modules directory
    """
    try:
        discovered = manager.discover_modules()
        logger.info(f"Refreshed module discovery - found {len(discovered)} modules")
        
        return APIResponse(
            success=True,
            message=f"Refreshed module discovery - found {len(discovered)} modules",
            data={'discovered_count': len(discovered), 'modules': discovered}
        )
        
    except Exception as e:
        logger.error(f"Error refreshing modules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@router.get("/health", response_model=APIResponse, summary="Module system health check")
async def health_check():
    """
    Check module system health
    """
    try:
        manager = ModuleManager()
        
        # Test basic operations
        installed = manager.get_installed_modules()
        discovered = manager.discover_modules()
        
        health_data = {
            'status': 'healthy',
            'database_accessible': True,
            'modules_directory_exists': manager.modules_dir.exists(),
            'installed_modules_count': len(installed),
            'discovered_modules_count': len(discovered)
        }
        
        return APIResponse(
            success=True,
            message="Module system is healthy",
            data=health_data
        )
        
    except Exception as e:
        logger.error(f"Module system health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Module system unhealthy: {e}")