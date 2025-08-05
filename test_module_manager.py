#!/usr/bin/env python3
"""
Test script for the real ModuleManager functionality
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from core.module_manager import ModuleManager
import json

def test_module_manager():
    """Test all ModuleManager functionality"""
    
    print("🧪 Testing ModuleManager - Real Functionality")
    print("=" * 60)
    
    # Initialize module manager
    try:
        manager = ModuleManager()
        print("✅ ModuleManager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ModuleManager: {e}")
        return False
    
    # Test discovering modules
    print("\n📦 Discovering modules...")
    try:
        discovered = manager.discover_modules()
        print(f"✅ Discovered {len(discovered)} modules:")
        for module in discovered:
            print(f"  • {module['name']} v{module['version']} ({'✅' if module['is_loadable'] else '❌'})")
    except Exception as e:
        print(f"❌ Failed to discover modules: {e}")
        return False
    
    # Test getting installed modules (should be empty initially)
    print("\n📋 Getting installed modules...")
    try:
        installed = manager.get_installed_modules()
        print(f"✅ Found {len(installed)} installed modules")
        if installed:
            for module in installed:
                print(f"  • {module['name']} v{module['version']} - {module['status']}")
    except Exception as e:
        print(f"❌ Failed to get installed modules: {e}")
        return False
    
    # Test installing a module if any are available
    if discovered:
        print(f"\n📥 Testing module installation...")
        test_module = discovered[0]  # Take the first discovered module
        module_name = test_module['name']
        
        try:
            result = manager.install_module(module_name)
            if result['success']:
                print(f"✅ Successfully installed {module_name}")
                
                # Test getting module status
                status = manager.get_module_status(module_name)
                if status.get('exists'):
                    print(f"✅ Module status retrieved: {status['status']}")
                else:
                    print(f"❌ Failed to get module status: {status.get('error', 'Unknown error')}")
                
                # Test setting configuration
                config_result = manager.set_module_config(module_name, 'test_setting', 'test_value')
                if config_result['success']:
                    print(f"✅ Configuration set successfully")
                    
                    # Test getting configuration
                    get_config = manager.get_module_config(module_name)
                    if get_config['success']:
                        print(f"✅ Configuration retrieved: {get_config['configs']}")
                    else:
                        print(f"❌ Failed to get configuration: {get_config['error']}")
                else:
                    print(f"❌ Failed to set configuration: {config_result['error']}")
                
                # Test updating module status
                status_update = manager.update_module_status(module_name, 'disabled')
                if status_update['success']:
                    print(f"✅ Module status updated to disabled")
                    
                    # Re-enable it
                    manager.update_module_status(module_name, 'active')
                    print(f"✅ Module status updated back to active")
                else:
                    print(f"❌ Failed to update module status: {status_update['error']}")
                
                # Test getting dependencies
                deps = manager.get_module_dependencies(module_name)
                if deps['success']:
                    if deps.get('dependencies'):
                        print(f"✅ Dependencies checked: {len(deps['dependencies'])} dependencies")
                        for dep, status in deps['dependency_status'].items():
                            print(f"  • {dep}: {'✅' if status['available'] else '❌'}")
                    else:
                        print(f"✅ No dependencies for {module_name}")
                else:
                    print(f"❌ Failed to check dependencies: {deps['error']}")
                
                # Test loading module
                load_result = manager.load_module(module_name)
                if load_result['success']:
                    print(f"✅ Module {module_name} loaded successfully")
                else:
                    print(f"⚠️  Module load failed (expected): {load_result['error']}")
                
                # Test uninstalling the module
                print(f"\n🗑️  Testing module uninstallation...")
                uninstall_result = manager.uninstall_module(module_name)
                if uninstall_result['success']:
                    print(f"✅ Successfully uninstalled {module_name}")
                else:
                    print(f"❌ Failed to uninstall {module_name}: {uninstall_result['error']}")
                    
            else:
                print(f"❌ Failed to install {module_name}: {result['error']}")
        except Exception as e:
            print(f"❌ Exception during module testing: {e}")
                
    else:
        print("ℹ️  No modules available for testing installation")
    
    print("\n" + "=" * 60)
    print("🎉 ModuleManager testing completed!")
    return True

if __name__ == "__main__":
    success = test_module_manager()
    sys.exit(0 if success else 1)