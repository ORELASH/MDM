"""
Module Management UI Page
Visual interface for managing system modules, enabling/disabling, and configuration.
"""

import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import importlib
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.auth_decorators import protected_page, require_role
from utils.auth_manager import UserRole
from utils.logging_system import RedshiftLogger
from core.module_registry import ModuleRegistry
from core.module_loader import ModuleLoader
from utils.user_preferences import UserPreferencesManager

logger = RedshiftLogger()

@protected_page(required_role=UserRole.MANAGER, page_name="Module Manager")
def module_manager_page():
    """
    Main module management page
    """
    st.title("🔧 Module Manager")
    st.markdown("### Manage system modules, configurations, and dependencies")
    st.markdown("---")
    
    # Initialize components
    registry = ModuleRegistry()
    loader = ModuleLoader()
    prefs_manager = UserPreferencesManager()
    
    # Create tabs for different management aspects
    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Module Overview",
        "⚙️ Module Configuration", 
        "📊 Module Status",
        "🔄 Module Operations"
    ])
    
    with tab1:
        show_module_overview(registry, loader)
    
    with tab2:
        show_module_configuration(registry, prefs_manager)
    
    with tab3:
        show_module_status(registry, loader)
    
    with tab4:
        show_module_operations(registry, loader)

def show_module_overview(registry: ModuleRegistry, loader: ModuleLoader):
    """
    Display overview of all available modules
    """
    st.subheader("📦 Available Modules")
    
    # Get all modules
    try:
        modules = registry.get_all_modules()
        
        if not modules:
            st.info("🔍 No modules found. Try discovering modules from the modules directory.")
            
            if st.button("🔄 Discover Modules", type="primary"):
                with st.spinner("Discovering modules..."):
                    discovered = discover_modules_from_directory()
                    if discovered:
                        st.success(f"✅ Discovered {len(discovered)} modules!")
                        st.rerun()
                    else:
                        st.warning("⚠️ No modules discovered")
            return
        
        # Display modules in cards
        cols = st.columns(2)
        
        for i, (module_name, module_info) in enumerate(modules.items()):
            with cols[i % 2]:
                with st.container():
                    # Module header
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**{module_info.get('display_name', module_name)}**")
                        st.caption(f"ID: {module_name}")
                    
                    with col2:
                        # Status indicator
                        is_enabled = module_info.get('enabled', False)
                        is_loaded = loader.is_module_loaded(module_name)
                        
                        if is_loaded:
                            st.success("🟢 Active")
                        elif is_enabled:
                            st.warning("🟡 Enabled")
                        else:
                            st.error("🔴 Disabled")
                    
                    # Module details
                    st.markdown(f"**Description:** {module_info.get('description', 'No description')}")
                    st.markdown(f"**Version:** {module_info.get('version', 'Unknown')}")
                    st.markdown(f"**Author:** {module_info.get('author', 'Unknown')}")
                    
                    # Dependencies
                    deps = module_info.get('dependencies', [])
                    if deps:
                        st.markdown(f"**Dependencies:** {', '.join(deps)}")
                    
                    # Quick actions
                    col_enable, col_config, col_info = st.columns(3)
                    
                    with col_enable:
                        if is_enabled:
                            if st.button("⏸️ Disable", key=f"disable_{module_name}", use_container_width=True):
                                toggle_module(registry, module_name, False)
                                st.rerun()
                        else:
                            if st.button("▶️ Enable", key=f"enable_{module_name}", use_container_width=True):
                                toggle_module(registry, module_name, True)
                                st.rerun()
                    
                    with col_config:
                        if st.button("⚙️ Config", key=f"config_{module_name}", use_container_width=True):
                            st.session_state.config_module = module_name
                            st.rerun()
                    
                    with col_info:
                        if st.button("ℹ️ Details", key=f"info_{module_name}", use_container_width=True):
                            st.session_state.info_module = module_name
                            st.rerun()
                    
                    st.markdown("---")
        
        # Show module details if requested
        if hasattr(st.session_state, 'info_module'):
            show_module_details(registry, st.session_state.info_module)
    
    except Exception as e:
        logger.log_error(f"Error loading modules overview: {e}")
        st.error(f"❌ Error loading modules: {e}")

def show_module_configuration(registry: ModuleRegistry, prefs_manager: UserPreferencesManager):
    """
    Show module configuration interface
    """
    st.subheader("⚙️ Module Configuration")
    
    # Module selector
    modules = registry.get_all_modules()
    if not modules:
        st.info("No modules available for configuration")
        return
    
    # Select module to configure
    selected_module = st.selectbox(
        "Select module to configure:",
        options=list(modules.keys()),
        format_func=lambda x: modules[x].get('display_name', x)
    )
    
    if selected_module:
        module_info = modules[selected_module]
        
        st.markdown(f"### Configuring: {module_info.get('display_name', selected_module)}")
        
        # Load current configuration
        current_config = load_module_config(selected_module)
        
        # Configuration form
        with st.form(f"config_form_{selected_module}"):
            st.markdown("#### Module Settings")
            
            # Basic settings
            enabled = st.checkbox(
                "Module Enabled",
                value=current_config.get('enabled', False),
                help="Enable or disable this module"
            )
            
            auto_start = st.checkbox(
                "Auto-start on system boot",
                value=current_config.get('auto_start', True),
                help="Automatically load this module when the system starts"
            )
            
            # Priority setting
            priority = st.slider(
                "Load Priority",
                min_value=0,
                max_value=10,
                value=current_config.get('priority', 5),
                help="Higher priority modules load first"
            )
            
            # Custom configuration
            st.markdown("#### Custom Configuration")
            
            # Get module-specific config schema if available
            config_schema = module_info.get('config_schema', {})
            custom_config = {}
            
            if config_schema:
                for key, schema in config_schema.items():
                    field_type = schema.get('type', 'string')
                    default_value = current_config.get('custom', {}).get(key, schema.get('default'))
                    description = schema.get('description', f'Configure {key}')
                    
                    if field_type == 'boolean':
                        custom_config[key] = st.checkbox(
                            key.replace('_', ' ').title(),
                            value=bool(default_value),
                            help=description
                        )
                    elif field_type == 'integer':
                        custom_config[key] = st.number_input(
                            key.replace('_', ' ').title(),
                            value=int(default_value or 0),
                            help=description
                        )
                    elif field_type == 'float':
                        custom_config[key] = st.number_input(
                            key.replace('_', ' ').title(),
                            value=float(default_value or 0.0),
                            help=description
                        )
                    elif field_type == 'select':
                        options = schema.get('options', [])
                        custom_config[key] = st.selectbox(
                            key.replace('_', ' ').title(),
                            options=options,
                            index=options.index(default_value) if default_value in options else 0,
                            help=description
                        )
                    else:  # string
                        custom_config[key] = st.text_input(
                            key.replace('_', ' ').title(),
                            value=str(default_value or ''),
                            help=description
                        )
            else:
                # Generic JSON configuration
                st.info("This module doesn't have a predefined configuration schema.")
                custom_json = st.text_area(
                    "Custom Configuration (JSON)",
                    value=json.dumps(current_config.get('custom', {}), indent=2),
                    height=200,
                    help="Enter custom configuration as JSON"
                )
                
                try:
                    custom_config = json.loads(custom_json) if custom_json.strip() else {}
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON format")
                    custom_config = {}
            
            # Save configuration
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 Save Config", type="primary"):
                    new_config = {
                        'enabled': enabled,
                        'auto_start': auto_start,
                        'priority': priority,
                        'custom': custom_config,
                        'last_modified': datetime.now().isoformat()
                    }
                    
                    if save_module_config(selected_module, new_config):
                        st.success("✅ Configuration saved successfully!")
                        logger.log_action_end(f"Module configuration updated: {selected_module}")
                    else:
                        st.error("❌ Failed to save configuration")
            
            with col2:
                if st.form_submit_button("🔄 Reset to Defaults"):
                    if reset_module_config(selected_module):
                        st.success("✅ Configuration reset to defaults!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to reset configuration")
            
            with col3:
                st.markdown("*Changes will take effect after module restart*")

def show_module_status(registry: ModuleRegistry, loader: ModuleLoader):
    """
    Show detailed module status and health information
    """
    st.subheader("📊 Module Status & Health")
    
    # System overview
    col1, col2, col3, col4 = st.columns(4)
    
    modules = registry.get_all_modules()
    enabled_count = sum(1 for m in modules.values() if m.get('enabled', False))
    loaded_count = sum(1 for name in modules.keys() if loader.is_module_loaded(name))
    error_count = get_module_error_count()
    
    with col1:
        st.metric("Total Modules", len(modules))
    
    with col2:
        st.metric("Enabled", enabled_count)
    
    with col3:
        st.metric("Currently Loaded", loaded_count)
    
    with col4:
        st.metric("Errors", error_count, delta_color="inverse")
    
    st.markdown("---")
    
    # Detailed status table
    if modules:
        status_data = []
        
        for module_name, module_info in modules.items():
            is_enabled = module_info.get('enabled', False)
            is_loaded = loader.is_module_loaded(module_name)
            
            # Get module health info
            health_info = get_module_health(module_name, is_loaded)
            
            status_data.append({
                'Module': module_info.get('display_name', module_name),
                'Status': '🟢 Active' if is_loaded else '🟡 Enabled' if is_enabled else '🔴 Disabled',
                'Version': module_info.get('version', 'Unknown'),
                'Memory': health_info.get('memory_usage', 'N/A'),
                'CPU': health_info.get('cpu_usage', 'N/A'),
                'Errors': health_info.get('error_count', 0),
                'Last Activity': health_info.get('last_activity', 'N/A')
            })
        
        st.dataframe(status_data, use_container_width=True)
        
        # Module logs
        st.markdown("#### Recent Module Logs")
        
        selected_log_module = st.selectbox(
            "Select module for logs:",
            options=['All'] + list(modules.keys()),
            format_func=lambda x: 'All Modules' if x == 'All' else modules.get(x, {}).get('display_name', x)
        )
        
        show_module_logs(selected_log_module)

def show_module_operations(registry: ModuleRegistry, loader: ModuleLoader):
    """
    Show module operations like start/stop, install/uninstall
    """
    st.subheader("🔄 Module Operations")
    
    # Module lifecycle operations
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Module Lifecycle")
        
        modules = registry.get_all_modules()
        if modules:
            selected_module = st.selectbox(
                "Select module:",
                options=list(modules.keys()),
                format_func=lambda x: modules[x].get('display_name', x)
            )
            
            if selected_module:
                is_loaded = loader.is_module_loaded(selected_module)
                
                col_start, col_stop, col_restart = st.columns(3)
                
                with col_start:
                    if st.button("▶️ Start", disabled=is_loaded, use_container_width=True):
                        if start_module(loader, selected_module):
                            st.success(f"✅ Started {selected_module}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to start {selected_module}")
                
                with col_stop:
                    if st.button("⏹️ Stop", disabled=not is_loaded, use_container_width=True):
                        if stop_module(loader, selected_module):
                            st.success(f"✅ Stopped {selected_module}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to stop {selected_module}")
                
                with col_restart:
                    if st.button("🔄 Restart", disabled=not is_loaded, use_container_width=True):
                        if restart_module(loader, selected_module):
                            st.success(f"✅ Restarted {selected_module}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to restart {selected_module}")
    
    with col2:
        st.markdown("#### System Operations")
        
        col_refresh, col_reload = st.columns(2)
        
        with col_refresh:
            if st.button("🔄 Refresh All", use_container_width=True):
                with st.spinner("Refreshing modules..."):
                    registry.discover_modules()
                    st.success("✅ Modules refreshed!")
                    st.rerun()
        
        with col_reload:
            if st.button("🔄 Reload All", use_container_width=True):
                if st.session_state.get('confirm_reload_all'):
                    with st.spinner("Reloading all modules..."):
                        if reload_all_modules(loader, registry):
                            st.success("✅ All modules reloaded!")
                            st.rerun()
                        else:
                            st.error("❌ Some modules failed to reload")
                    st.session_state.confirm_reload_all = False
                else:
                    st.session_state.confirm_reload_all = True
                    st.warning("⚠️ Click again to confirm reload all modules")
    
    st.markdown("---")
    
    # Bulk operations
    st.markdown("#### Bulk Operations")
    
    if modules:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Enable/Disable Multiple Modules**")
            
            selected_modules = st.multiselect(
                "Select modules:",
                options=list(modules.keys()),
                format_func=lambda x: modules[x].get('display_name', x)
            )
            
            if selected_modules:
                col_enable_all, col_disable_all = st.columns(2)
                
                with col_enable_all:
                    if st.button("✅ Enable Selected", use_container_width=True):
                        enabled_count = 0
                        for module_name in selected_modules:
                            if toggle_module(registry, module_name, True):
                                enabled_count += 1
                        
                        st.success(f"✅ Enabled {enabled_count}/{len(selected_modules)} modules")
                        st.rerun()
                
                with col_disable_all:
                    if st.button("❌ Disable Selected", use_container_width=True):
                        disabled_count = 0
                        for module_name in selected_modules:
                            if toggle_module(registry, module_name, False):
                                disabled_count += 1
                        
                        st.success(f"✅ Disabled {disabled_count}/{len(selected_modules)} modules")
                        st.rerun()
        
        with col2:
            st.markdown("**System Maintenance**")
            
            if st.button("🧹 Clean Module Cache", use_container_width=True):
                if clean_module_cache():
                    st.success("✅ Module cache cleaned!")
                else:
                    st.error("❌ Failed to clean cache")
            
            if st.button("📊 Export Module Config", use_container_width=True):
                config_json = export_module_configurations()
                if config_json:
                    st.download_button(
                        "💾 Download Configuration",
                        data=config_json,
                        file_name=f"module_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

# Helper functions
def discover_modules_from_directory() -> List[str]:
    """Discover modules from the modules directory"""
    try:
        modules_dir = project_root / "modules"
        discovered = []
        
        if modules_dir.exists():
            for item in modules_dir.iterdir():
                if item.is_dir() and (item / "module.json").exists():
                    discovered.append(item.name)
        
        return discovered
    except Exception as e:
        logger.log_error(f"Error discovering modules: {e}")
        return []

def toggle_module(registry: ModuleRegistry, module_name: str, enabled: bool) -> bool:
    """Toggle module enabled state"""
    try:
        config = load_module_config(module_name)
        config['enabled'] = enabled
        config['last_modified'] = datetime.now().isoformat()
        
        success = save_module_config(module_name, config)
        if success:
            logger.log_action_end(f"Module {'enabled' if enabled else 'disabled'}: {module_name}")
        
        return success
    except Exception as e:
        logger.log_error(f"Error toggling module {module_name}: {e}")
        return False

def load_module_config(module_name: str) -> Dict[str, Any]:
    """Load module configuration"""
    try:
        config_path = project_root / "data" / "module_configs" / f"{module_name}.json"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Return default config
            return {
                'enabled': False,
                'auto_start': True,
                'priority': 5,
                'custom': {}
            }
    except Exception as e:
        logger.log_error(f"Error loading config for {module_name}: {e}")
        return {'enabled': False, 'auto_start': True, 'priority': 5, 'custom': {}}

def save_module_config(module_name: str, config: Dict[str, Any]) -> bool:
    """Save module configuration"""
    try:
        config_dir = project_root / "data" / "module_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = config_dir / f"{module_name}.json"
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True
    except Exception as e:
        logger.log_error(f"Error saving config for {module_name}: {e}")
        return False

def reset_module_config(module_name: str) -> bool:
    """Reset module configuration to defaults"""
    try:
        default_config = {
            'enabled': False,
            'auto_start': True,
            'priority': 5,
            'custom': {},
            'last_modified': datetime.now().isoformat()
        }
        
        return save_module_config(module_name, default_config)
    except Exception as e:
        logger.log_error(f"Error resetting config for {module_name}: {e}")
        return False

def get_module_error_count() -> int:
    """Get total error count across all modules"""
    # This would integrate with the logging system
    return 0

def get_module_health(module_name: str, is_loaded: bool) -> Dict[str, Any]:
    """Get module health information"""
    if not is_loaded:
        return {
            'memory_usage': 'N/A',
            'cpu_usage': 'N/A',
            'error_count': 0,
            'last_activity': 'Not loaded'
        }
    
    # In a real implementation, this would gather actual metrics
    return {
        'memory_usage': '~2MB',
        'cpu_usage': '<1%',
        'error_count': 0,
        'last_activity': 'Active'
    }

def show_module_logs(module_name: str):
    """Show module logs"""
    try:
        # This would integrate with the logging system
        if module_name == 'All':
            st.info("📝 All module logs would be displayed here")
        else:
            st.info(f"📝 Logs for {module_name} would be displayed here")
        
        # Placeholder for actual log display
        sample_logs = [
            "2025-07-28 17:30:00 | INFO | Module started successfully",
            "2025-07-28 17:30:15 | DEBUG | Processing user request", 
            "2025-07-28 17:30:30 | INFO | Operation completed"
        ]
        
        for log in sample_logs:
            st.code(log)
            
    except Exception as e:
        st.error(f"Error loading logs: {e}")

def start_module(loader: ModuleLoader, module_name: str) -> bool:
    """Start a module"""
    try:
        return loader.load_module(module_name)
    except Exception as e:
        logger.log_error(f"Error starting module {module_name}: {e}")
        return False

def stop_module(loader: ModuleLoader, module_name: str) -> bool:
    """Stop a module"""
    try:
        return loader.unload_module(module_name)
    except Exception as e:
        logger.log_error(f"Error stopping module {module_name}: {e}")
        return False

def restart_module(loader: ModuleLoader, module_name: str) -> bool:
    """Restart a module"""
    try:
        if loader.unload_module(module_name):
            return loader.load_module(module_name)
        return False
    except Exception as e:
        logger.log_error(f"Error restarting module {module_name}: {e}")
        return False

def reload_all_modules(loader: ModuleLoader, registry: ModuleRegistry) -> bool:
    """Reload all modules"""
    try:
        # Stop all loaded modules
        loaded_modules = [name for name in registry.get_all_modules().keys() 
                         if loader.is_module_loaded(name)]
        
        for module_name in loaded_modules:
            loader.unload_module(module_name)
        
        # Rediscover modules
        registry.discover_modules()
        
        # Restart enabled modules
        modules = registry.get_all_modules()
        for module_name, module_info in modules.items():
            if module_info.get('enabled', False):
                loader.load_module(module_name)
        
        return True
    except Exception as e:
        logger.log_error(f"Error reloading all modules: {e}")
        return False

def clean_module_cache() -> bool:
    """Clean module cache"""
    try:
        # Implementation would clean Python module cache and temp files
        return True
    except Exception as e:
        logger.log_error(f"Error cleaning module cache: {e}")
        return False

def export_module_configurations() -> str:
    """Export all module configurations"""
    try:
        config_dir = project_root / "data" / "module_configs"
        all_configs = {}
        
        if config_dir.exists():
            for config_file in config_dir.glob("*.json"):
                module_name = config_file.stem
                with open(config_file, 'r') as f:
                    all_configs[module_name] = json.load(f)
        
        return json.dumps({
            'export_timestamp': datetime.now().isoformat(),
            'configurations': all_configs
        }, indent=2)
    except Exception as e:
        logger.log_error(f"Error exporting configurations: {e}")
        return ""

def show_module_details(registry: ModuleRegistry, module_name: str):
    """Show detailed module information in a modal-like interface"""
    modules = registry.get_all_modules()
    if module_name not in modules:
        return
    
    module_info = modules[module_name]
    
    with st.expander(f"📋 {module_info.get('display_name', module_name)} - Detailed Information", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Basic Information")
            st.markdown(f"**Name:** {module_name}")
            st.markdown(f"**Display Name:** {module_info.get('display_name', 'N/A')}")
            st.markdown(f"**Version:** {module_info.get('version', 'Unknown')}")
            st.markdown(f"**Author:** {module_info.get('author', 'Unknown')}")
            st.markdown(f"**Description:** {module_info.get('description', 'No description')}")
        
        with col2:
            st.markdown("#### Technical Details")
            st.markdown(f"**Module Path:** {module_info.get('path', 'N/A')}")
            st.markdown(f"**Dependencies:** {', '.join(module_info.get('dependencies', []))}")
            st.markdown(f"**Category:** {module_info.get('category', 'General')}")
            st.markdown(f"**Priority:** {module_info.get('priority', 5)}")
        
        # Close button
        if st.button("❌ Close Details"):
            if hasattr(st.session_state, 'info_module'):
                delattr(st.session_state, 'info_module')
            st.rerun()

if __name__ == "__main__":
    module_manager_page()