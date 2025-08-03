#!/usr/bin/env python3
"""
Group to Role Mapping System
Maps Active Directory groups to database roles automatically
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
import logging

class GroupRoleMapper:
    """Manages mapping between AD groups and database roles"""
    
    def __init__(self, mapping_file: str = None):
        self.mapping_file = mapping_file or "/home/orel/my_installer/rsm/RedshiftManager/config/group_role_mappings.json"
        self.logger = logging.getLogger(__name__)
        
        # Initialize mapping directory
        Path(os.path.dirname(self.mapping_file)).mkdir(parents=True, exist_ok=True)
        
        # Load mappings
        self.mappings = self.load_mappings()
    
    def load_mappings(self) -> Dict:
        """Load group-to-role mappings from file"""
        default_mappings = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "mappings": {
                # Database-specific mappings
                "postgresql": {},
                "mysql": {},
                "redshift": {},
                "global": {}  # Universal mappings applied to all databases
            },
            "templates": {
                # Pre-defined role templates
                "data_analyst": {
                    "description": "Basic data analyst permissions",
                    "roles": ["readonly", "connect"],
                    "permissions": ["SELECT"]
                },
                "data_engineer": {
                    "description": "Data engineering permissions",
                    "roles": ["readwrite", "connect"],
                    "permissions": ["SELECT", "INSERT", "UPDATE", "DELETE"]
                },
                "admin": {
                    "description": "Administrative permissions",
                    "roles": ["superuser", "admin"],
                    "permissions": ["ALL"]
                }
            },
            "settings": {
                "auto_assign_roles": True,
                "create_missing_roles": False,
                "case_sensitive": False,
                "sync_on_ldap_update": True
            }
        }
        
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
                    # Merge with defaults for any missing keys
                    for key, value in default_mappings.items():
                        if key not in mappings:
                            mappings[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in mappings[key]:
                                    mappings[key][subkey] = subvalue
                    return mappings
            else:
                # Create default mapping file
                with open(self.mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(default_mappings, f, indent=2, ensure_ascii=False)
                return default_mappings
                
        except Exception as e:
            self.logger.error(f"Error loading group mappings: {e}")
            return default_mappings
    
    def save_mappings(self):
        """Save mappings to file"""
        try:
            self.mappings["updated_at"] = datetime.now().isoformat()
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving group mappings: {e}")
    
    def add_group_mapping(self, group_name: str, database_type: str, roles: List[str], 
                         description: str = None, overwrite: bool = False) -> bool:
        """Add a mapping between AD group and database roles"""
        try:
            # Normalize group name based on settings
            if not self.mappings.get("settings", {}).get("case_sensitive", False):
                group_key = group_name.lower()
            else:
                group_key = group_name
            
            # Check if mapping already exists
            if database_type not in self.mappings["mappings"]:
                self.mappings["mappings"][database_type] = {}
            
            if group_key in self.mappings["mappings"][database_type] and not overwrite:
                self.logger.warning(f"Mapping for group {group_name} in {database_type} already exists")
                return False
            
            # Add mapping
            mapping = {
                "original_group_name": group_name,
                "roles": roles,
                "description": description or f"Auto-generated mapping for {group_name}",
                "created_at": datetime.now().isoformat(),
                "active": True
            }
            
            self.mappings["mappings"][database_type][group_key] = mapping
            self.save_mappings()
            
            self.logger.info(f"Added mapping: {group_name} -> {roles} for {database_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding group mapping: {e}")
            return False
    
    def remove_group_mapping(self, group_name: str, database_type: str) -> bool:
        """Remove a group mapping"""
        try:
            # Normalize group name
            if not self.mappings.get("settings", {}).get("case_sensitive", False):
                group_key = group_name.lower()
            else:
                group_key = group_name
            
            if (database_type in self.mappings["mappings"] and 
                group_key in self.mappings["mappings"][database_type]):
                
                del self.mappings["mappings"][database_type][group_key]
                self.save_mappings()
                
                self.logger.info(f"Removed mapping for group {group_name} in {database_type}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing group mapping: {e}")
            return False
    
    def get_roles_for_user(self, user_groups: List[str], database_type: str) -> List[str]:
        """Get database roles for a user based on their AD groups"""
        roles = set()
        
        try:
            # Normalize group names
            case_sensitive = self.mappings.get("settings", {}).get("case_sensitive", False)
            normalized_groups = user_groups if case_sensitive else [g.lower() for g in user_groups]
            
            # Check database-specific mappings
            db_mappings = self.mappings["mappings"].get(database_type, {})
            for group_key, mapping in db_mappings.items():
                if mapping.get("active", True):
                    # Check if user is in this group
                    if case_sensitive:
                        if mapping.get("original_group_name", group_key) in user_groups:
                            roles.update(mapping.get("roles", []))
                    else:
                        if group_key in normalized_groups:
                            roles.update(mapping.get("roles", []))
            
            # Check global mappings (apply to all databases)
            global_mappings = self.mappings["mappings"].get("global", {})
            for group_key, mapping in global_mappings.items():
                if mapping.get("active", True):
                    if case_sensitive:
                        if mapping.get("original_group_name", group_key) in user_groups:
                            roles.update(mapping.get("roles", []))
                    else:
                        if group_key in normalized_groups:
                            roles.update(mapping.get("roles", []))
            
            result = list(roles)
            if result:
                self.logger.debug(f"Mapped groups {user_groups} to roles {result} for {database_type}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting roles for user groups: {e}")
            return []
    
    def get_all_mappings(self, database_type: str = None) -> Dict:
        """Get all mappings, optionally filtered by database type"""
        if database_type:
            return self.mappings["mappings"].get(database_type, {})
        return self.mappings["mappings"]
    
    def get_mapping_statistics(self) -> Dict:
        """Get statistics about current mappings"""
        stats = {
            "total_mappings": 0,
            "by_database": {},
            "active_mappings": 0,
            "inactive_mappings": 0,
            "most_common_roles": {},
            "templates_available": len(self.mappings.get("templates", {}))
        }
        
        try:
            all_roles = []
            
            for db_type, mappings in self.mappings["mappings"].items():
                db_count = len(mappings)
                stats["by_database"][db_type] = db_count
                stats["total_mappings"] += db_count
                
                for mapping in mappings.values():
                    if mapping.get("active", True):
                        stats["active_mappings"] += 1
                    else:
                        stats["inactive_mappings"] += 1
                    
                    all_roles.extend(mapping.get("roles", []))
            
            # Count role frequency
            from collections import Counter
            role_counts = Counter(all_roles)
            stats["most_common_roles"] = dict(role_counts.most_common(10))
            
        except Exception as e:
            self.logger.error(f"Error calculating mapping statistics: {e}")
        
        return stats
    
    def apply_template(self, template_name: str, group_name: str, database_type: str) -> bool:
        """Apply a pre-defined template to a group mapping"""
        try:
            template = self.mappings.get("templates", {}).get(template_name)
            if not template:
                self.logger.error(f"Template {template_name} not found")
                return False
            
            roles = template.get("roles", [])
            description = f"Applied template '{template_name}': {template.get('description', '')}"
            
            return self.add_group_mapping(
                group_name=group_name,
                database_type=database_type,
                roles=roles,
                description=description,
                overwrite=True
            )
            
        except Exception as e:
            self.logger.error(f"Error applying template: {e}")
            return False
    
    def bulk_import_mappings(self, mappings_data: List[Dict]) -> Tuple[int, int]:
        """Bulk import mappings from data"""
        success_count = 0
        error_count = 0
        
        for mapping_data in mappings_data:
            try:
                group_name = mapping_data.get("group_name")
                database_type = mapping_data.get("database_type", "global")
                roles = mapping_data.get("roles", [])
                description = mapping_data.get("description")
                
                if not group_name or not roles:
                    error_count += 1
                    continue
                
                if self.add_group_mapping(group_name, database_type, roles, description, overwrite=True):
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                self.logger.error(f"Error importing mapping {mapping_data}: {e}")
                error_count += 1
        
        return success_count, error_count
    
    def export_mappings(self, database_type: str = None) -> List[Dict]:
        """Export mappings in a standard format"""
        exported = []
        
        try:
            mappings_to_export = {}
            if database_type:
                mappings_to_export[database_type] = self.mappings["mappings"].get(database_type, {})
            else:
                mappings_to_export = self.mappings["mappings"]
            
            for db_type, mappings in mappings_to_export.items():
                for group_key, mapping in mappings.items():
                    exported.append({
                        "group_name": mapping.get("original_group_name", group_key),
                        "database_type": db_type,
                        "roles": mapping.get("roles", []),
                        "description": mapping.get("description", ""),
                        "active": mapping.get("active", True),
                        "created_at": mapping.get("created_at", "")
                    })
        
        except Exception as e:
            self.logger.error(f"Error exporting mappings: {e}")
        
        return exported
    
    def suggest_mappings_for_groups(self, groups: List[str]) -> Dict[str, List[str]]:
        """Suggest role mappings for new groups based on naming patterns"""
        suggestions = {}
        
        # Common patterns and suggested roles
        patterns = {
            # Admin patterns
            r'(?i).*(admin|administrator|superuser|dba).*': ['admin', 'superuser'],
            r'(?i).*(root|sysadmin).*': ['admin', 'superuser'],
            
            # Developer patterns  
            r'(?i).*(dev|developer|engineer).*': ['readwrite', 'connect'],
            r'(?i).*(backend|fullstack).*': ['readwrite', 'connect'],
            
            # Analyst patterns
            r'(?i).*(analyst|analytics|bi|business.intelligence).*': ['readonly', 'connect'],
            r'(?i).*(report|reporting).*': ['readonly', 'connect'],
            
            # Data patterns
            r'(?i).*(data.scientist|ds|datascience).*': ['readwrite', 'connect'],
            r'(?i).*(etl|pipeline).*': ['readwrite', 'connect', 'create'],
            
            # Read-only patterns
            r'(?i).*(readonly|read.only|viewer).*': ['readonly', 'connect'],
            r'(?i).*(guest|temp|temporary).*': ['readonly']
        }
        
        import re
        
        for group in groups:
            suggested_roles = []
            
            for pattern, roles in patterns.items():
                if re.match(pattern, group):
                    suggested_roles.extend(roles)
                    break
            
            if not suggested_roles:
                # Default suggestion
                suggested_roles = ['connect']
            
            suggestions[group] = list(set(suggested_roles))  # Remove duplicates
        
        return suggestions
    
    def validate_roles_exist(self, roles: List[str], database_type: str, 
                           server_info: Dict) -> Tuple[List[str], List[str]]:
        """Validate that roles exist in the target database"""
        existing_roles = []
        missing_roles = []
        
        try:
            # This would integrate with the database connection
            # For now, return common roles as existing
            common_roles = {
                'postgresql': ['postgres', 'readonly', 'readwrite', 'connect', 'superuser'],
                'mysql': ['mysql', 'read', 'write', 'admin'],
                'redshift': ['readonly', 'readwrite', 'superuser', 'connect']
            }
            
            db_roles = common_roles.get(database_type, [])
            
            for role in roles:
                if role.lower() in [r.lower() for r in db_roles]:
                    existing_roles.append(role)
                else:
                    missing_roles.append(role)
        
        except Exception as e:
            self.logger.error(f"Error validating roles: {e}")
            missing_roles = roles
        
        return existing_roles, missing_roles

# Global group role mapper instance
_group_role_mapper = None

def get_group_role_mapper() -> GroupRoleMapper:
    """Get the global group role mapper instance"""
    global _group_role_mapper
    if _group_role_mapper is None:
        _group_role_mapper = GroupRoleMapper()
    return _group_role_mapper