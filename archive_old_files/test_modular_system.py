#!/usr/bin/env python3
"""
Test script for the Modular Core System
Demonstrates module discovery, loading, and action execution.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_modular_system():
    """Test the modular system functionality"""
    print("🔧 Testing RedshiftManager Modular Core System")
    print("=" * 60)
    
    try:
        # Import core components
        from core.modular_core import initialize_modular_core
        from core.action_framework import PopulationTarget, PopulationScope
        from core.security_manager import create_default_security_manager
        
        print("✅ Successfully imported core components")
        
        # Initialize the modular core
        print("\n🚀 Initializing Modular Core...")
        core = initialize_modular_core(
            core_version="1.0.0",
            config={
                "audit_log_max_entries": 1000,
                "module_discovery_paths": ["./modules"]
            }
        )
        
        # Set up security manager
        security_manager = create_default_security_manager()
        core.set_security_manager(security_manager)
        
        print("✅ Modular Core initialized")
        
        # Start the system
        print("\n🌟 Starting System...")
        if core.start_system(auto_discover=True):
            print("✅ System started successfully")
        else:
            print("❌ Failed to start system")
            return False
        
        # Show system status
        print("\n📊 System Status:")
        status = core.get_system_status()
        for key, value in status.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
        
        # List discovered modules
        print("\n🔍 Discovered Modules:")
        modules = core.list_modules()
        for module_name in modules:
            module_info = core.get_module_info(module_name)
            status_icon = "🟢" if module_info['loaded'] else "🔴"
            active_icon = "🟢" if module_info.get('active', False) else "🔴"
            print(f"  {status_icon} {module_name} - Loaded: {module_info['loaded']}, Active: {active_icon}")
        
        # Test module loading
        print("\n📦 Testing Module Loading...")
        if "sample_analytics" in modules:
            print("Loading sample_analytics module...")
            if core.load_module("sample_analytics"):
                print("✅ Module loaded successfully")
                
                # Activate the module
                print("Activating sample_analytics module...")
                if core.activate_module("sample_analytics"):
                    print("✅ Module activated successfully")
                    
                    # Test module health
                    health = core.loader.get_module_health("sample_analytics")
                    print(f"Module health: {health}")
                    
                else:
                    print("❌ Failed to activate module")
            else:
                print("❌ Failed to load module")
        else:
            print("⚠️ sample_analytics module not found")
        
        # Test action framework
        print("\n⚡ Testing Action Framework...")
        action_catalog = core.get_action_catalog()
        print("Available action types:")
        for action_type, info in action_catalog.items():
            print(f"  {action_type}: {info['count']} actions")
            for action in info['actions']:
                print(f"    - {action['name']}: {action['description']}")
        
        # Test population targeting
        print("\n🎯 Testing Population Targeting...")
        supported_types = core.get_supported_target_types()
        print(f"Supported target types: {supported_types}")
        
        # Create a simple population target for testing
        from core.action_framework import PopulationTarget, PopulationScope
        test_target = PopulationTarget(
            scope=PopulationScope.ALL,
            target_type="cluster"
        )
        
        # Preview the target
        preview = core.preview_population(test_target, limit=5)
        print(f"Population preview: {preview}")
        
        # Test action execution (if analytics action is available)
        if "analyze_query_performance" in [action['name'] for actions in action_catalog.values() for action in actions['actions']]:
            print("\n🔄 Testing Action Execution...")
            execution_id = core.execute_action(
                action_name="analyze_query_performance",
                population_target=test_target,
                parameters={
                    "time_range_days": 7,
                    "include_successful_only": False,
                    "min_execution_time": 0.0
                },
                user_id="test_user"
            )
            
            if execution_id:
                print(f"✅ Action execution started with ID: {execution_id}")
                
                # Check execution status
                status = core.get_execution_status(execution_id)
                if status:
                    print(f"Execution status: {status['status']}")
                    if status.get('result'):
                        print(f"Result: {status['result']}")
            else:
                print("❌ Failed to execute action")
        
        # Test UI components
        print("\n🖥️ Testing UI Components...")
        ui_components = core.get_ui_components()
        if ui_components:
            for module_name, components in ui_components.items():
                print(f"Module {module_name} UI components:")
                for comp_type, comps in components.items():
                    print(f"  {comp_type}: {list(comps.keys()) if isinstance(comps, dict) else comps}")
        else:
            print("No UI components registered")
        
        # Test event system
        print("\n📡 Testing Event System...")
        
        def test_event_handler(data):
            print(f"  📨 Received test event with data: {data}")
        
        core.subscribe_event("test_event", test_event_handler)
        core.emit_event("test_event", {"message": "Hello from modular system!"})
        
        # Module health report
        print("\n🏥 Module Health Report:")
        health_report = core.get_module_health_report()
        for module_name, health in health_report.items():
            status_icon = "✅" if health.get('healthy', False) else "❌"
            print(f"  {status_icon} {module_name}: {health.get('status', 'unknown')}")
        
        # Shutdown test
        print("\n🛑 Testing System Shutdown...")
        if core.shutdown_system():
            print("✅ System shutdown successfully")
        else:
            print("❌ Failed to shutdown system")
        
        print("\n🎉 Modular System Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_module_creation():
    """Test creating a simple module programmatically"""
    print("\n🛠️ Testing Module Creation...")
    
    try:
        from core.plugin_interface import ModuleBase, ModuleManifest, ModuleType
        
        # Create a simple test module
        class TestModule(ModuleBase):
            def on_initialize(self) -> bool:
                self.context.logger.info("Test module initialized")
                return True
            
            def on_activate(self) -> bool:
                self.context.logger.info("Test module activated")
                return True
            
            def on_deactivate(self) -> bool:
                self.context.logger.info("Test module deactivated")
                return True
            
            def get_ui_components(self):
                return {
                    'widgets': {
                        'test_widget': lambda: print("Test widget rendered")
                    }
                }
        
        # Create manifest
        manifest = ModuleManifest(
            name="test_module",
            version="1.0.0",
            description="Programmatically created test module",
            author="Test",
            module_type=ModuleType.UTILITY,
            core_version_min="1.0.0"
        )
        
        print("✅ Successfully created test module class and manifest")
        return True
        
    except Exception as e:
        print(f"❌ Module creation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running Modular System Tests")
    
    # Test module creation
    test_module_creation()
    
    # Test full system
    success = test_modular_system()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)