"""
Population Manager for RedshiftManager
Handles targeting and selection of populations for action execution.
"""

from typing import Dict, List, Any, Optional, Set, Callable
from abc import ABC, abstractmethod
import logging
from dataclasses import dataclass
import re

from .action_framework import PopulationTarget, PopulationScope


@dataclass
class PopulationGroup:
    """Predefined group of targets"""
    name: str
    description: str
    target_type: str
    target_ids: List[str]
    filters: Dict[str, Any]
    created_by: str
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TargetResolver(ABC):
    """Abstract base class for target resolvers"""
    
    @abstractmethod
    def get_target_type(self) -> str:
        """Return the target type this resolver handles"""
        pass
    
    @abstractmethod
    def resolve_all(self) -> List[Any]:
        """Get all available targets of this type"""
        pass
    
    @abstractmethod
    def resolve_by_ids(self, target_ids: List[str]) -> List[Any]:
        """Resolve targets by their IDs"""
        pass
    
    @abstractmethod
    def resolve_by_filters(self, filters: Dict[str, Any]) -> List[Any]:
        """Resolve targets using filters"""
        pass
    
    @abstractmethod
    def get_target_info(self, target: Any) -> Dict[str, Any]:
        """Get information about a target for display"""
        pass


class ClusterTargetResolver(TargetResolver):
    """Resolver for Redshift cluster targets"""
    
    def __init__(self, core_instance):
        self.core = core_instance
        self.logger = logging.getLogger("resolver.cluster")
    
    def get_target_type(self) -> str:
        return "cluster"
    
    def resolve_all(self) -> List[Any]:
        """Get all available clusters"""
        try:
            from models.database_models import RedshiftCluster, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                clusters = session.query(RedshiftCluster).filter_by(is_active=True).all()
                return clusters
        except Exception as e:
            self.logger.error(f"Error resolving all clusters: {e}")
            return []
    
    def resolve_by_ids(self, target_ids: List[str]) -> List[Any]:
        """Resolve clusters by IDs"""
        try:
            from models.database_models import RedshiftCluster, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                clusters = session.query(RedshiftCluster).filter(
                    RedshiftCluster.id.in_(target_ids),
                    RedshiftCluster.is_active == True
                ).all()
                return clusters
        except Exception as e:
            self.logger.error(f"Error resolving clusters by IDs: {e}")
            return []
    
    def resolve_by_filters(self, filters: Dict[str, Any]) -> List[Any]:
        """Resolve clusters using filters"""
        try:
            from models.database_models import RedshiftCluster, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                query = session.query(RedshiftCluster).filter_by(is_active=True)
                
                # Apply filters
                if 'environment' in filters:
                    query = query.filter(RedshiftCluster.environment == filters['environment'])
                
                if 'name_pattern' in filters:
                    pattern = filters['name_pattern']
                    query = query.filter(RedshiftCluster.name.like(f"%{pattern}%"))
                
                if 'tags' in filters:
                    # Assuming clusters have tags stored as JSON
                    for tag in filters['tags']:
                        query = query.filter(RedshiftCluster.tags.contains(tag))
                
                if 'created_after' in filters:
                    query = query.filter(RedshiftCluster.created_at >= filters['created_after'])
                
                clusters = query.all()
                return clusters
        except Exception as e:
            self.logger.error(f"Error resolving clusters by filters: {e}")
            return []
    
    def get_target_info(self, target: Any) -> Dict[str, Any]:
        """Get cluster information"""
        return {
            'id': target.id,
            'name': target.name,
            'host': target.host,
            'environment': target.environment,
            'description': target.description,
            'created_at': target.created_at.isoformat() if target.created_at else None
        }


class UserTargetResolver(TargetResolver):
    """Resolver for user targets"""
    
    def __init__(self, core_instance):
        self.core = core_instance
        self.logger = logging.getLogger("resolver.user")
    
    def get_target_type(self) -> str:
        return "user"
    
    def resolve_all(self) -> List[Any]:
        """Get all active users"""
        try:
            from models.database_models import User, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                users = session.query(User).filter_by(is_active=True).all()
                return users
        except Exception as e:
            self.logger.error(f"Error resolving all users: {e}")
            return []
    
    def resolve_by_ids(self, target_ids: List[str]) -> List[Any]:
        """Resolve users by IDs"""
        try:
            from models.database_models import User, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                users = session.query(User).filter(
                    User.id.in_(target_ids),
                    User.is_active == True
                ).all()
                return users
        except Exception as e:
            self.logger.error(f"Error resolving users by IDs: {e}")
            return []
    
    def resolve_by_filters(self, filters: Dict[str, Any]) -> List[Any]:
        """Resolve users using filters"""
        try:
            from models.database_models import User, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                query = session.query(User).filter_by(is_active=True)
                
                # Apply filters
                if 'role' in filters:
                    # Filter by role (assuming many-to-many relationship)
                    query = query.join(User.roles).filter_by(name=filters['role'])
                
                if 'email_domain' in filters:
                    domain = filters['email_domain']
                    query = query.filter(User.email.like(f"%@{domain}"))
                
                if 'created_after' in filters:
                    query = query.filter(User.created_at >= filters['created_after'])
                
                if 'last_login_before' in filters:
                    query = query.filter(User.last_login_at <= filters['last_login_before'])
                
                users = query.all()
                return users
        except Exception as e:
            self.logger.error(f"Error resolving users by filters: {e}")
            return []
    
    def get_target_info(self, target: Any) -> Dict[str, Any]:
        """Get user information"""
        return {
            'id': target.id,
            'username': target.username,
            'email': target.email,
            'full_name': f"{target.first_name} {target.last_name}",
            'roles': [role.name for role in target.roles],
            'last_login': target.last_login_at.isoformat() if target.last_login_at else None
        }


class QueryTargetResolver(TargetResolver):
    """Resolver for query targets (from history)"""
    
    def __init__(self, core_instance):
        self.core = core_instance
        self.logger = logging.getLogger("resolver.query")
    
    def get_target_type(self) -> str:
        return "query"
    
    def resolve_all(self) -> List[Any]:
        """Get recent queries"""
        try:
            from models.database_models import QueryHistory, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                queries = session.query(QueryHistory).order_by(
                    QueryHistory.created_at.desc()
                ).limit(1000).all()
                return queries
        except Exception as e:
            self.logger.error(f"Error resolving all queries: {e}")
            return []
    
    def resolve_by_ids(self, target_ids: List[str]) -> List[Any]:
        """Resolve queries by IDs"""
        try:
            from models.database_models import QueryHistory, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                queries = session.query(QueryHistory).filter(
                    QueryHistory.id.in_(target_ids)
                ).all()
                return queries
        except Exception as e:
            self.logger.error(f"Error resolving queries by IDs: {e}")
            return []
    
    def resolve_by_filters(self, filters: Dict[str, Any]) -> List[Any]:
        """Resolve queries using filters"""
        try:
            from models.database_models import QueryHistory, get_database_manager
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                query = session.query(QueryHistory)
                
                # Apply filters
                if 'cluster_id' in filters:
                    query = query.filter(QueryHistory.cluster_id == filters['cluster_id'])
                
                if 'user_id' in filters:
                    query = query.filter(QueryHistory.user_id == filters['user_id'])
                
                if 'query_type' in filters:
                    query = query.filter(QueryHistory.query_type == filters['query_type'])
                
                if 'success_only' in filters and filters['success_only']:
                    query = query.filter(QueryHistory.success == True)
                
                if 'failed_only' in filters and filters['failed_only']:
                    query = query.filter(QueryHistory.success == False)
                
                if 'execution_time_min' in filters:
                    query = query.filter(QueryHistory.execution_time >= filters['execution_time_min'])
                
                if 'execution_time_max' in filters:
                    query = query.filter(QueryHistory.execution_time <= filters['execution_time_max'])
                
                if 'created_after' in filters:
                    query = query.filter(QueryHistory.created_at >= filters['created_after'])
                
                if 'text_contains' in filters:
                    text = filters['text_contains']
                    query = query.filter(QueryHistory.query_text.contains(text))
                
                queries = query.order_by(QueryHistory.created_at.desc()).all()
                return queries
        except Exception as e:
            self.logger.error(f"Error resolving queries by filters: {e}")
            return []
    
    def get_target_info(self, target: Any) -> Dict[str, Any]:
        """Get query information"""
        return {
            'id': target.id,
            'query_type': target.query_type,
            'execution_time': target.execution_time,
            'rows_affected': target.rows_affected,
            'success': target.success,
            'created_at': target.created_at.isoformat() if target.created_at else None,
            'preview': target.query_text[:100] + "..." if len(target.query_text) > 100 else target.query_text
        }


class PopulationManager:
    """
    Manages population targeting and resolution for action execution.
    """
    
    def __init__(self, core_instance):
        self.core = core_instance
        self.resolvers: Dict[str, TargetResolver] = {}
        self.groups: Dict[str, PopulationGroup] = {}
        self.logger = logging.getLogger("core.population")
        
        # Register built-in resolvers
        self._register_builtin_resolvers()
    
    def _register_builtin_resolvers(self):
        """Register built-in target resolvers"""
        self.register_resolver(ClusterTargetResolver(self.core))
        self.register_resolver(UserTargetResolver(self.core))
        self.register_resolver(QueryTargetResolver(self.core))
    
    def register_resolver(self, resolver: TargetResolver):
        """Register a target resolver"""
        target_type = resolver.get_target_type()
        self.resolvers[target_type] = resolver
        self.logger.info(f"Registered resolver for target type: {target_type}")
    
    def unregister_resolver(self, target_type: str):
        """Unregister a target resolver"""
        if target_type in self.resolvers:
            del self.resolvers[target_type]
            self.logger.info(f"Unregistered resolver for target type: {target_type}")
    
    def get_supported_target_types(self) -> List[str]:
        """Get list of supported target types"""
        return list(self.resolvers.keys())
    
    def resolve_targets(self, population_target: PopulationTarget) -> List[Any]:
        """Resolve a population target to actual objects"""
        target_type = population_target.target_type
        
        if target_type not in self.resolvers:
            self.logger.error(f"No resolver for target type: {target_type}")
            return []
        
        resolver = self.resolvers[target_type]
        
        try:
            if population_target.scope == PopulationScope.ALL:
                return resolver.resolve_all()
            
            elif population_target.scope == PopulationScope.SINGLE:
                if population_target.target_ids:
                    targets = resolver.resolve_by_ids([population_target.target_ids[0]])
                    return targets[:1]  # Return only the first one
                return []
            
            elif population_target.scope == PopulationScope.MULTIPLE:
                if population_target.target_ids:
                    return resolver.resolve_by_ids(population_target.target_ids)
                return []
            
            elif population_target.scope == PopulationScope.GROUP:
                if population_target.group_name and population_target.group_name in self.groups:
                    group = self.groups[population_target.group_name]
                    if group.target_type == target_type:
                        # Combine group target IDs and additional filters
                        combined_ids = group.target_ids + population_target.target_ids
                        targets = resolver.resolve_by_ids(combined_ids) if combined_ids else []
                        
                        # Apply additional filters if any
                        if population_target.filters:
                            # This is a simplified approach - in reality you'd want to 
                            # apply filters to the already resolved targets
                            filtered_targets = resolver.resolve_by_filters(population_target.filters)
                            # Intersect the two sets
                            target_ids = {str(getattr(t, 'id', t)) for t in targets}
                            targets = [t for t in filtered_targets 
                                     if str(getattr(t, 'id', t)) in target_ids]
                        
                        return targets
                return []
            
            elif population_target.scope == PopulationScope.FILTERED:
                if population_target.filters:
                    return resolver.resolve_by_filters(population_target.filters)
                return []
            
            else:
                self.logger.error(f"Unknown population scope: {population_target.scope}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error resolving targets: {e}")
            return []
    
    def get_target_info(self, target_type: str, targets: List[Any]) -> List[Dict[str, Any]]:
        """Get information about resolved targets"""
        if target_type not in self.resolvers:
            return []
        
        resolver = self.resolvers[target_type]
        return [resolver.get_target_info(target) for target in targets]
    
    def create_group(self, group: PopulationGroup) -> bool:
        """Create a new population group"""
        if group.name in self.groups:
            self.logger.warning(f"Group {group.name} already exists")
            return False
        
        # Validate that target type is supported
        if group.target_type not in self.resolvers:
            self.logger.error(f"Unsupported target type for group: {group.target_type}")
            return False
        
        self.groups[group.name] = group
        self.logger.info(f"Created population group: {group.name}")
        return True
    
    def update_group(self, group_name: str, updates: Dict[str, Any]) -> bool:
        """Update an existing population group"""
        if group_name not in self.groups:
            self.logger.error(f"Group {group_name} not found")
            return False
        
        group = self.groups[group_name]
        
        # Update allowed fields
        if 'description' in updates:
            group.description = updates['description']
        if 'target_ids' in updates:
            group.target_ids = updates['target_ids']
        if 'filters' in updates:
            group.filters = updates['filters']
        if 'tags' in updates:
            group.tags = updates['tags']
        
        self.logger.info(f"Updated population group: {group_name}")
        return True
    
    def delete_group(self, group_name: str) -> bool:
        """Delete a population group"""
        if group_name in self.groups:
            del self.groups[group_name]
            self.logger.info(f"Deleted population group: {group_name}")
            return True
        return False
    
    def get_group(self, group_name: str) -> Optional[PopulationGroup]:
        """Get a population group"""
        return self.groups.get(group_name)
    
    def list_groups(self, target_type: Optional[str] = None) -> List[PopulationGroup]:
        """List population groups, optionally filtered by target type"""
        groups = list(self.groups.values())
        if target_type:
            groups = [g for g in groups if g.target_type == target_type]
        return groups
    
    def validate_population_target(self, target: PopulationTarget) -> List[str]:
        """Validate a population target"""
        errors = []
        
        # Check if target type is supported
        if target.target_type not in self.resolvers:
            errors.append(f"Unsupported target type: {target.target_type}")
            return errors
        
        # Validate based on scope
        if target.scope == PopulationScope.SINGLE:
            if not target.target_ids or len(target.target_ids) != 1:
                errors.append("Single scope requires exactly one target ID")
        
        elif target.scope == PopulationScope.MULTIPLE:
            if not target.target_ids:
                errors.append("Multiple scope requires at least one target ID")
        
        elif target.scope == PopulationScope.GROUP:
            if not target.group_name:
                errors.append("Group scope requires a group name")
            elif target.group_name not in self.groups:
                errors.append(f"Group '{target.group_name}' not found")
            elif self.groups[target.group_name].target_type != target.target_type:
                errors.append(f"Group target type mismatch")
        
        elif target.scope == PopulationScope.FILTERED:
            if not target.filters:
                errors.append("Filtered scope requires filters")
        
        return errors
    
    def preview_targets(self, target: PopulationTarget, limit: int = 10) -> Dict[str, Any]:
        """Preview targets that would be resolved (for UI display)"""
        try:
            resolved_targets = self.resolve_targets(target)
            limited_targets = resolved_targets[:limit]
            
            target_info = self.get_target_info(target.target_type, limited_targets)
            
            return {
                'total_count': len(resolved_targets),
                'preview_count': len(limited_targets),
                'targets': target_info,
                'truncated': len(resolved_targets) > limit
            }
        except Exception as e:
            self.logger.error(f"Error previewing targets: {e}")
            return {
                'total_count': 0,
                'preview_count': 0,
                'targets': [],
                'truncated': False,
                'error': str(e)
            }