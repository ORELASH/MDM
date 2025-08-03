#!/usr/bin/env python3
"""
Development Check Script for RedshiftManager
Comprehensive testing and validation for development environment.
"""

import sys
import os
import traceback
from pathlib import Path
import importlib.util
import time
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "RedshiftManager"))

# Import our logging system
try:
    from utils.logging_config import get_logger, log_function
    logger = get_logger("dev_check")
    logger.info("🚀 Starting development check", timestamp=datetime.now().isoformat())
except Exception as e:
    print(f"❌ Failed to setup logging: {e}")
    # Fallback to basic logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("dev_check")
    # Create a dummy log_function decorator for fallback
    def log_function(logger_instance, func_name):
        def decorator(func):
            return func
        return decorator


class DevChecker:
    """Development environment checker"""
    
    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'info': []
        }
        self.start_time = time.time()
    
    def check_all(self):
        """Run all development checks"""
        logger.info("🔍 Starting comprehensive development checks")
        
        # Core system checks
        self.check_python_environment()
        self.check_dependencies()
        self.check_file_structure()
        
        # Core module checks
        self.check_core_modules()
        self.check_modular_system()
        
        # Application checks
        self.check_application_structure()
        self.check_dashboard()
        self.check_translations()
        
        # Integration checks
        self.check_database_models()
        self.check_sample_module()
        
        # Development environment checks
        self.check_logging_system()
        self.check_development_files()
        
        # Generate report
        self.generate_report()
    
    @log_function(logger, "check_python_environment")
    def check_python_environment(self):
        """Check Python environment"""
        try:
            # Python version
            python_version = sys.version_info
            if python_version >= (3, 8):
                self.results['passed'].append(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
            else:
                self.results['failed'].append(f"❌ Python version too old: {python_version}")
            
            # Working directory
            cwd = os.getcwd()
            if "rsm" in cwd:
                self.results['passed'].append(f"✅ Working directory: {cwd}")
            else:
                self.results['warnings'].append(f"⚠️  Working directory might be wrong: {cwd}")
            
            # Python path
            self.results['info'].append(f"ℹ️  Python executable: {sys.executable}")
            
        except Exception as e:
            self.results['failed'].append(f"❌ Python environment check failed: {e}")
            logger.error(f"Python environment check failed: {e}")
    
    @log_function(logger, "check_dependencies")
    def check_dependencies(self):
        """Check required dependencies"""
        required_packages = [
            'streamlit', 'sqlalchemy', 'pandas', 'plotly', 
            'cryptography', 'psycopg2', 'bcrypt'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                self.results['passed'].append(f"✅ {package}")
                logger.debug(f"Package {package} is available")
            except ImportError:
                self.results['failed'].append(f"❌ Missing package: {package}")
                logger.error(f"Missing package: {package}")
    
    @log_function(logger, "check_file_structure")
    def check_file_structure(self):
        """Check project file structure"""
        required_dirs = [
            "core", "models", "utils", "config", "modules",
            "RedshiftManager", "RedshiftManager/pages", 
            "RedshiftManager/translations"
        ]
        
        required_files = [
            "core/__init__.py", "core/modular_core.py",
            "models/__init__.py", "models/database_models.py",
            "utils/__init__.py", "utils/logging_config.py",
            "RedshiftManager/main.py",
            "RedshiftManager/pages/dashboard.py",
            "test_modular_system.py"
        ]
        
        # Check directories
        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                self.results['passed'].append(f"✅ Directory: {dir_path}")
            else:
                self.results['failed'].append(f"❌ Missing directory: {dir_path}")
        
        # Check files
        for file_path in required_files:
            path = Path(file_path)
            if path.exists() and path.is_file():
                self.results['passed'].append(f"✅ File: {file_path}")
                logger.debug(f"File exists: {file_path}")
            else:
                self.results['failed'].append(f"❌ Missing file: {file_path}")
                logger.error(f"Missing file: {file_path}")
    
    @log_function(logger, "check_core_modules")
    def check_core_modules(self):
        """Check core modules can be imported"""
        core_modules = [
            "core.modular_core",
            "core.module_registry", 
            "core.module_loader",
            "core.plugin_interface",
            "core.action_framework",
            "core.population_manager",
            "core.security_manager"
        ]
        
        for module_name in core_modules:
            try:
                module = importlib.import_module(module_name)
                self.results['passed'].append(f"✅ Core module: {module_name}")
                logger.debug(f"Successfully imported {module_name}")
            except Exception as e:
                self.results['failed'].append(f"❌ Failed to import {module_name}: {e}")
                logger.error(f"Failed to import {module_name}: {e}")
    
    @log_function(logger, "check_modular_system")
    def check_modular_system(self):
        """Check modular system functionality"""
        try:
            from core.modular_core import initialize_modular_core
            from core.security_manager import create_default_security_manager
            
            # Initialize core
            logger.info("Initializing modular core for testing")
            core = initialize_modular_core(core_version="1.0.0")
            core.set_security_manager(create_default_security_manager())
            
            # Start system
            if core.start_system(auto_discover=True):
                self.results['passed'].append("✅ Modular system startup")
                logger.info("Modular system started successfully")
                
                # Check system status
                status = core.get_system_status()
                self.results['info'].append(f"ℹ️  System status: {status['system_started']}")
                self.results['info'].append(f"ℹ️  Modules registered: {status['modules']['total_registered']}")
                
                # Shutdown system
                if core.shutdown_system():
                    self.results['passed'].append("✅ Modular system shutdown")
                else:
                    self.results['failed'].append("❌ Modular system shutdown failed")
            else:
                self.results['failed'].append("❌ Modular system startup failed")
                
        except Exception as e:
            self.results['failed'].append(f"❌ Modular system check failed: {e}")
            logger.error(f"Modular system check failed: {e}")
    
    @log_function(logger, "check_application_structure")
    def check_application_structure(self):
        """Check RedshiftManager application structure"""
        try:
            # Check main application
            from RedshiftManager.main import main, check_dependencies
            self.results['passed'].append("✅ Main application import")
            
            # Check dependencies function
            missing_deps = check_dependencies()
            if not missing_deps:
                self.results['passed'].append("✅ Application dependencies")
            else:
                self.results['warnings'].append(f"⚠️  Missing app dependencies: {missing_deps}")
            
            # Check pages
            pages = ['cluster_management', 'user_management', 'query_execution', 'settings', 'dashboard']
            for page in pages:
                try:
                    module = importlib.import_module(f"RedshiftManager.pages.{page}")
                    self.results['passed'].append(f"✅ Page: {page}")
                except Exception as e:
                    self.results['failed'].append(f"❌ Page {page}: {e}")
            
        except Exception as e:
            self.results['failed'].append(f"❌ Application structure check failed: {e}")
            logger.error(f"Application structure check failed: {e}")
    
    @log_function(logger, "check_dashboard")
    def check_dashboard(self):
        """Check dashboard functionality"""
        try:
            from RedshiftManager.pages.dashboard import dashboard_page, get_cluster_count, get_user_count
            self.results['passed'].append("✅ Dashboard import")
            
            # Test helper functions
            cluster_count = get_cluster_count()
            user_count = get_user_count()
            
            self.results['info'].append(f"ℹ️  Cluster count: {cluster_count}")
            self.results['info'].append(f"ℹ️  User count: {user_count}")
            
            logger.info(f"Dashboard check completed - cluster_count: {cluster_count}, user_count: {user_count}")
            
        except Exception as e:
            self.results['failed'].append(f"❌ Dashboard check failed: {e}")
            logger.error(f"Dashboard check failed: {e}")
    
    @log_function(logger, "check_translations")
    def check_translations(self):
        """Check translation system"""
        try:
            from RedshiftManager.utils.i18n_helper import get_text, load_translations
            
            # Test translation loading
            translations = load_translations('en')
            if translations:
                self.results['passed'].append("✅ Translation loading")
                
                # Check dashboard translations
                dashboard_keys = [k for k in translations.keys() if k.startswith('dashboard.')]
                self.results['info'].append(f"ℹ️  Dashboard translation keys: {len(dashboard_keys)}")
                
                # Test translation function
                test_text = get_text("nav.dashboard", "Dashboard")
                self.results['passed'].append(f"✅ Translation function: '{test_text}'")
                
            else:
                self.results['failed'].append("❌ Translation loading failed")
                
        except Exception as e:
            self.results['failed'].append(f"❌ Translation check failed: {e}")
            logger.error(f"Translation check failed: {e}")
    
    @log_function(logger, "check_database_models")
    def check_database_models(self):
        """Check database models"""
        try:
            from models.database_models import get_database_manager, User, RedshiftCluster
            
            # Test database manager
            db_manager = get_database_manager()
            self.results['passed'].append("✅ Database manager")
            
            # Test models
            self.results['passed'].append("✅ Database models import")
            
            logger.info("Database models check completed")
            
        except Exception as e:
            self.results['failed'].append(f"❌ Database models check failed: {e}")
            logger.error(f"Database models check failed: {e}")
    
    @log_function(logger, "check_sample_module")
    def check_sample_module(self):
        """Check sample analytics module"""
        try:
            sample_module_path = Path("modules/sample_analytics")
            if sample_module_path.exists():
                # Check module.json
                module_json = sample_module_path / "module.json"
                if module_json.exists():
                    import json
                    with open(module_json) as f:
                        module_data = json.load(f)
                    self.results['passed'].append("✅ Sample module manifest")
                    self.results['info'].append(f"ℹ️  Sample module version: {module_data.get('version', 'unknown')}")
                
                # Check module code
                module_init = sample_module_path / "__init__.py"
                if module_init.exists():
                    self.results['passed'].append("✅ Sample module code")
                else:
                    self.results['failed'].append("❌ Sample module __init__.py missing")
            else:
                self.results['failed'].append("❌ Sample module directory missing")
                
        except Exception as e:
            self.results['failed'].append(f"❌ Sample module check failed: {e}")
            logger.error(f"Sample module check failed: {e}")
    
    @log_function(logger, "check_logging_system")
    def check_logging_system(self):
        """Check logging system"""
        try:
            from utils.logging_config import get_dev_logger, setup_global_logging
            
            # Test logger creation
            test_logger = get_dev_logger("test")
            self.results['passed'].append("✅ Logging system")
            
            # Test different log levels
            test_logger.debug("Test debug message")
            test_logger.info("Test info message")
            test_logger.warning("Test warning message")
            
            # Check logs directory
            logs_dir = Path("logs")
            if logs_dir.exists():
                log_files = list(logs_dir.glob("*.log"))
                self.results['passed'].append(f"✅ Log files created: {len(log_files)}")
            else:
                self.results['warnings'].append("⚠️  Logs directory not found")
            
        except Exception as e:
            self.results['failed'].append(f"❌ Logging system check failed: {e}")
            logger.error(f"Logging system check failed: {e}")
    
    @log_function(logger, "check_development_files")
    def check_development_files(self):
        """Check development and documentation files"""
        dev_files = [
            "TASK_PLAN.md",
            "PROGRESS_TRACKER.md", 
            "TODO_MANAGEMENT.md",
            "COMPLETE_ROADMAP.md",
            "DAILY_LOG_27_07_2025.md",
            "TOMORROW_TASKS.md"
        ]
        
        for file_name in dev_files:
            file_path = Path(file_name)
            if file_path.exists():
                self.results['passed'].append(f"✅ Dev file: {file_name}")
            else:
                self.results['warnings'].append(f"⚠️  Dev file missing: {file_name}")
    
    def generate_report(self):
        """Generate comprehensive development check report"""
        duration = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("🔍 REDSHIFTMANAGER DEVELOPMENT CHECK REPORT")
        print("="*80)
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Summary
        total_passed = len(self.results['passed'])
        total_failed = len(self.results['failed'])
        total_warnings = len(self.results['warnings'])
        total_checks = total_passed + total_failed + total_warnings
        
        print(f"📊 SUMMARY:")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   ⚠️  Warnings: {total_warnings}")
        print(f"   📋 Total: {total_checks}")
        print()
        
        # Success rate
        if total_checks > 0:
            success_rate = (total_passed / total_checks) * 100
            print(f"🎯 Success Rate: {success_rate:.1f}%")
        
        # Status
        if total_failed == 0:
            print("🎉 STATUS: READY FOR DEVELOPMENT")
        elif total_failed <= 2:
            print("⚠️  STATUS: MINOR ISSUES - CAN PROCEED WITH CAUTION")
        else:
            print("❌ STATUS: MAJOR ISSUES - NEEDS ATTENTION")
        
        print()
        
        # Detailed results
        if self.results['passed']:
            print("✅ PASSED CHECKS:")
            for item in self.results['passed']:
                print(f"   {item}")
            print()
        
        if self.results['failed']:
            print("❌ FAILED CHECKS:")
            for item in self.results['failed']:
                print(f"   {item}")
            print()
        
        if self.results['warnings']:
            print("⚠️  WARNINGS:")
            for item in self.results['warnings']:
                print(f"   {item}")
            print()
        
        if self.results['info']:
            print("ℹ️  INFORMATION:")
            for item in self.results['info']:
                print(f"   {item}")
            print()
        
        # Next steps
        print("🚀 NEXT STEPS:")
        if total_failed == 0:
            print("   1. ✅ All systems ready!")
            print("   2. 🎯 Continue with today's tasks from TOMORROW_TASKS.md")
            print("   3. 🚀 Start with dashboard integration testing")
        else:
            print("   1. 🔧 Fix failed checks above")
            print("   2. 🔄 Re-run this check: python dev_check.py")
            print("   3. 📚 Check documentation for troubleshooting")
        
        print("="*80)
        
        # Log final result
        success_rate_str = f"{success_rate:.1f}%" if total_checks > 0 else "N/A"
        logger.info(f"Development check completed - passed: {total_passed}, failed: {total_failed}, warnings: {total_warnings}, success_rate: {success_rate_str}")


def main():
    """Main function"""
    print("🚀 RedshiftManager Development Environment Check")
    print("Starting comprehensive system validation...")
    print()
    
    try:
        checker = DevChecker()
        checker.check_all()
        
    except Exception as e:
        print(f"❌ Development check failed with critical error: {e}")
        print("\nTraceback:")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())