#!/usr/bin/env python3
"""
Migration Script: JSON to SQLite
Migrate MultiDBManager from JSON file storage to SQLite database
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("migration")

def backup_existing_data(data_dir: str = "data"):
    """Create backup of existing JSON data"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"data_backup_{timestamp}"
    
    if os.path.exists(data_dir):
        shutil.copytree(data_dir, backup_dir)
        logger.info(f"Backed up existing data to: {backup_dir}")
        return backup_dir
    else:
        logger.warning(f"Data directory {data_dir} not found")
        return None

def analyze_existing_data(data_dir: str = "data"):
    """Analyze existing JSON data to understand structure"""
    analysis = {
        'servers_count': 0,
        'session_files': 0,
        'total_users': 0,
        'files_found': []
    }
    
    # Check servers.json
    servers_file = os.path.join(data_dir, "servers.json")
    if os.path.exists(servers_file):
        with open(servers_file, 'r') as f:
            servers = json.load(f)
            analysis['servers_count'] = len(servers)
            analysis['files_found'].append('servers.json')
            logger.info(f"Found {len(servers)} servers in servers.json")
    
    # Check session files
    sessions_dir = os.path.join(data_dir, "sessions")
    if os.path.exists(sessions_dir):
        session_count = 0
        user_count = 0
        
        for server_dir in os.listdir(sessions_dir):
            server_path = os.path.join(sessions_dir, server_dir)
            if os.path.isdir(server_path):
                latest_session = os.path.join(server_path, "session_latest.json")
                if os.path.exists(latest_session):
                    session_count += 1
                    try:
                        with open(latest_session, 'r') as f:
                            session_data = json.load(f)
                            users = session_data.get('scan_results', {}).get('users', [])
                            user_count += len(users)
                    except Exception as e:
                        logger.warning(f"Could not read session file {latest_session}: {e}")
        
        analysis['session_files'] = session_count
        analysis['total_users'] = user_count
        logger.info(f"Found {session_count} session files with {user_count} total users")
    
    # Check other files
    other_files = ['user_preferences', 'app_settings.json']
    for file_name in other_files:
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            analysis['files_found'].append(file_name)
    
    return analysis

def migrate_data(dry_run: bool = False):
    """Perform the actual migration"""
    from database.database_manager import DatabaseManager, JSONToSQLiteMigrator
    
    if dry_run:
        logger.info("DRY RUN MODE - No actual changes will be made")
        return
    
    try:
        # Initialize database
        logger.info("Initializing SQLite database...")
        db_manager = DatabaseManager()
        
        # Create migrator
        migrator = JSONToSQLiteMigrator(db_manager)
        
        # Perform migration
        logger.info("Starting data migration...")
        migrator.migrate_all()
        
        # Verify migration
        stats = db_manager.get_statistics()
        logger.info("Migration completed successfully!")
        logger.info(f"Migrated data summary:")
        logger.info(f"  - Servers: {stats['servers']['total']} ({stats['servers']['connected']} connected)")
        logger.info(f"  - Users: {stats['users']['total']} ({stats['users']['active']} active)")
        logger.info(f"  - Global unique users: {stats['global_users']['unique_users']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

def update_configuration_files():
    """Update configuration files to use SQLite"""
    config_updates = []
    
    # Update main.py if it exists
    main_py = "main.py"
    if os.path.exists(main_py):
        with open(main_py, 'r') as f:
            content = f.read()
        
        # Add database import
        if "from database.database_manager import get_database_manager" not in content:
            # Find imports section and add database import
            lines = content.split('\n')
            import_line = -1
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_line = i
            
            if import_line >= 0:
                lines.insert(import_line + 1, "from database.database_manager import get_database_manager")
                
                with open(main_py, 'w') as f:
                    f.write('\n'.join(lines))
                
                config_updates.append("Updated main.py with database import")
    
    # Create database configuration
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)
    
    db_config = {
        "database": {
            "type": "sqlite",
            "path": "data/multidb_manager.db",
            "backup_enabled": True,
            "backup_interval_hours": 24,
            "backup_retention_days": 30
        },
        "migration": {
            "completed": True,
            "migration_date": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    }
    
    config_file = os.path.join(config_dir, "database_config.json")
    with open(config_file, 'w') as f:
        json.dump(db_config, f, indent=2)
    
    config_updates.append(f"Created database configuration: {config_file}")
    
    return config_updates

def create_migration_report(backup_dir: str, analysis: dict, success: bool):
    """Create detailed migration report"""
    report = {
        "migration_info": {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "backup_location": backup_dir
        },
        "data_analysis": analysis,
        "post_migration_files": {
            "database": "data/multidb_manager.db",
            "config": "config/database_config.json",
            "schema": "database/schema.sql",
            "manager": "database/database_manager.py"
        },
        "next_steps": [
            "Update application code to use DatabaseManager",
            "Test database connectivity",
            "Verify data integrity",
            "Remove old JSON files (after verification)",
            "Update deployment scripts"
        ]
    }
    
    report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Migration report saved to: {report_file}")
    return report_file

def main():
    parser = argparse.ArgumentParser(description="Migrate MultiDBManager from JSON to SQLite")
    parser.add_argument("--dry-run", action="store_true", help="Analyze data without making changes")
    parser.add_argument("--no-backup", action="store_true", help="Skip backing up existing data")
    parser.add_argument("--data-dir", default="data", help="Data directory path")
    
    args = parser.parse_args()
    
    logger.info("MultiDBManager JSON to SQLite Migration")
    logger.info("=" * 50)
    
    # Step 1: Analyze existing data
    logger.info("Step 1: Analyzing existing data...")
    analysis = analyze_existing_data(args.data_dir)
    
    if analysis['servers_count'] == 0 and analysis['session_files'] == 0:
        logger.warning("No data found to migrate. This might be a fresh installation.")
        if not args.dry_run:
            # Still create the database structure
            from database.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            logger.info("Created empty SQLite database structure")
        return
    
    # Step 2: Backup existing data
    backup_dir = None
    if not args.no_backup and not args.dry_run:
        logger.info("Step 2: Backing up existing data...")
        backup_dir = backup_existing_data(args.data_dir)
    else:
        logger.info("Step 2: Skipping backup (dry-run or --no-backup)")
    
    # Step 3: Perform migration
    logger.info("Step 3: Performing migration...")
    try:
        success = migrate_data(args.dry_run)
        if success and not args.dry_run:
            logger.info("Migration successful!")
        elif args.dry_run:
            logger.info("Dry run completed - migration would succeed")
            success = True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        success = False
    
    # Step 4: Update configuration files
    if success and not args.dry_run:
        logger.info("Step 4: Updating configuration files...")
        config_updates = update_configuration_files()
        for update in config_updates:
            logger.info(f"  - {update}")
    
    # Step 5: Create migration report
    logger.info("Step 5: Creating migration report...")
    report_file = create_migration_report(backup_dir, analysis, success)
    
    # Summary
    logger.info("=" * 50)
    if success:
        logger.info("✅ Migration completed successfully!")
        if not args.dry_run:
            logger.info(f"📁 Backup created at: {backup_dir}")
            logger.info(f"📊 Database created at: data/redshift_manager.db")
            logger.info(f"📋 Report saved to: {report_file}")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Test the application with SQLite database")
            logger.info("2. Verify all data migrated correctly")
            logger.info("3. Update deployment scripts if needed")
            logger.info("4. Remove old JSON files after verification")
    else:
        logger.error("❌ Migration failed!")
        if backup_dir:
            logger.info(f"Your original data is safely backed up at: {backup_dir}")

if __name__ == "__main__":
    main()