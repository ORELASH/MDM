"""
Action Framework for RedshiftManager
Enables dynamic operations with population targeting and execution control.
"""

import inspect
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging


class ActionType(Enum):
    """Types of actions in the system"""
    QUERY = "query"
    MANAGEMENT = "management"
    MONITORING = "monitoring"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    REPORTING = "reporting"
    AUTOMATION = "automation"
    INTEGRATION = "integration"


class ActionStatus(Enum):
    """Action execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class PopulationScope(Enum):
    """Scope of population targeting"""
    SINGLE = "single"          # Single target (one cluster, one user, etc.)
    MULTIPLE = "multiple"      # Multiple specific targets
    GROUP = "group"            # Predefined group
    FILTERED = "filtered"      # Dynamic filter-based selection
    ALL = "all"               # All available targets


@dataclass
class ActionParameter:
    """Definition of an action parameter"""
    name: str
    param_type: str  # 'string', 'number', 'boolean', 'list', 'dict', 'cluster', 'user', etc.
    required: bool = True
    default_value: Any = None
    description: str = ""
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    ui_component: Optional[str] = None  # UI component type for rendering


@dataclass
class PopulationTarget:
    """Defines a target population for action execution"""
    scope: PopulationScope
    target_type: str  # 'cluster', 'user', 'database', 'query', etc.
    target_ids: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    group_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'scope': self.scope.value,
            'target_type': self.target_type,
            'target_ids': self.target_ids,
            'filters': self.filters,
            'group_name': self.group_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PopulationTarget':
        """Create from dictionary"""
        return cls(
            scope=PopulationScope(data['scope']),
            target_type=data['target_type'],
            target_ids=data.get('target_ids', []),
            filters=data.get('filters', {}),
            group_name=data.get('group_name')
        )


@dataclass
class ActionExecution:
    """Represents an action execution instance"""
    id: str
    action_name: str
    population_target: PopulationTarget
    parameters: Dict[str, Any]
    status: ActionStatus = ActionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    executed_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'action_name': self.action_name,
            'population_target': self.population_target.to_dict(),
            'parameters': self.parameters,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error_message': self.error_message,
            'progress': self.progress,
            'executed_by': self.executed_by
        }


class Action(ABC):
    """
    Base class for all actions in the system.
    Actions are operations that can be performed on populations of targets.
    """
    
    def __init__(self, name: str, action_type: ActionType, description: str = ""):
        self.name = name
        self.action_type = action_type
        self.description = description
        self.parameters: List[ActionParameter] = []
        self.supported_target_types: List[str] = []
        self.required_permissions: List[str] = []
        self.logger = logging.getLogger(f"action.{name}")
    
    def add_parameter(self, param: ActionParameter):
        """Add a parameter definition to the action"""
        self.parameters.append(param)
    
    def add_target_type(self, target_type: str):
        """Add a supported target type"""
        if target_type not in self.supported_target_types:
            self.supported_target_types.append(target_type)
    
    def add_permission(self, permission: str):
        """Add a required permission"""
        if permission not in self.required_permissions:
            self.required_permissions.append(permission)
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Validate action parameters.
        Returns list of validation errors (empty if valid).
        """
        pass
    
    @abstractmethod
    def validate_target(self, target: PopulationTarget) -> List[str]:
        """
        Validate population target for this action.
        Returns list of validation errors (empty if valid).
        """
        pass
    
    @abstractmethod
    def execute(self, target: PopulationTarget, parameters: Dict[str, Any], 
               execution_context: 'ActionExecutionContext') -> Dict[str, Any]:
        """
        Execute the action on the specified population target.
        Returns execution result.
        """
        pass
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Get JSON schema for action parameters"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in self.parameters:
            param_schema = {
                "type": param.param_type,
                "description": param.description
            }
            
            if param.default_value is not None:
                param_schema["default"] = param.default_value
            
            # Add validation rules
            param_schema.update(param.validation_rules)
            
            schema["properties"][param.name] = param_schema
            
            if param.required:
                schema["required"].append(param.name)
        
        return schema
    
    def get_info(self) -> Dict[str, Any]:
        """Get action information for UI/API"""
        return {
            "name": self.name,
            "type": self.action_type.value,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.param_type,
                    "required": p.required,
                    "default": p.default_value,
                    "description": p.description,
                    "ui_component": p.ui_component
                } for p in self.parameters
            ],
            "supported_target_types": self.supported_target_types,
            "required_permissions": self.required_permissions
        }


class ActionExecutionContext:
    """Context object passed to actions during execution"""
    
    def __init__(self, execution: ActionExecution, core_instance, user_id: str):
        self.execution = execution
        self.core = core_instance
        self.user_id = user_id
        self.logger = logging.getLogger(f"action.execution.{execution.id}")
        
    def update_progress(self, progress: float, message: str = ""):
        """Update execution progress"""
        self.execution.progress = min(100.0, max(0.0, progress))
        self.logger.info(f"Progress: {progress}% - {message}")
        
    def get_targets(self) -> List[Any]:
        """Resolve population target to actual objects"""
        return self.core.population_manager.resolve_targets(self.execution.population_target)
    
    def get_database_session(self):
        """Get database session"""
        return self.core.get_database_session()
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has required permission"""
        return self.core.security_manager.has_permission(self.user_id, permission)
    
    def log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit event"""
        self.core.log_audit(action, details, user_id=self.user_id, 
                           execution_id=self.execution.id)


class ActionFramework:
    """
    Central framework for managing and executing actions.
    """
    
    def __init__(self, core_instance):
        self.core = core_instance
        self.registered_actions: Dict[str, Action] = {}
        self.executions: Dict[str, ActionExecution] = {}
        self.logger = logging.getLogger("core.actions")
    
    def register_action(self, action: Action):
        """Register an action in the framework"""
        if action.name in self.registered_actions:
            self.logger.warning(f"Overriding existing action: {action.name}")
        
        self.registered_actions[action.name] = action
        self.logger.info(f"Registered action: {action.name} ({action.action_type.value})")
    
    def unregister_action(self, action_name: str):
        """Unregister an action"""
        if action_name in self.registered_actions:
            del self.registered_actions[action_name]
            self.logger.info(f"Unregistered action: {action_name}")
        else:
            self.logger.warning(f"Action not found for unregistration: {action_name}")
    
    def get_action(self, action_name: str) -> Optional[Action]:
        """Get a registered action"""
        return self.registered_actions.get(action_name)
    
    def list_actions(self, action_type: Optional[ActionType] = None) -> List[str]:
        """List registered actions, optionally filtered by type"""
        if action_type:
            return [name for name, action in self.registered_actions.items() 
                   if action.action_type == action_type]
        return list(self.registered_actions.keys())
    
    def get_actions_for_target_type(self, target_type: str) -> List[str]:
        """Get actions that support a specific target type"""
        return [name for name, action in self.registered_actions.items()
                if target_type in action.supported_target_types]
    
    def validate_execution_request(self, action_name: str, target: PopulationTarget, 
                                 parameters: Dict[str, Any], user_id: str) -> List[str]:
        """Validate an execution request"""
        errors = []
        
        # Check if action exists
        action = self.registered_actions.get(action_name)
        if not action:
            errors.append(f"Action '{action_name}' not found")
            return errors
        
        # Validate parameters
        param_errors = action.validate_parameters(parameters)
        errors.extend(param_errors)
        
        # Validate target
        target_errors = action.validate_target(target)
        errors.extend(target_errors)
        
        # Check permissions
        for permission in action.required_permissions:
            if not self.core.security_manager.has_permission(user_id, permission):
                errors.append(f"Missing required permission: {permission}")
        
        return errors
    
    def create_execution(self, action_name: str, target: PopulationTarget, 
                        parameters: Dict[str, Any], user_id: str) -> str:
        """Create a new action execution"""
        import uuid
        
        execution_id = str(uuid.uuid4())
        execution = ActionExecution(
            id=execution_id,
            action_name=action_name,
            population_target=target,
            parameters=parameters,
            executed_by=user_id
        )
        
        self.executions[execution_id] = execution
        self.logger.info(f"Created execution {execution_id} for action {action_name}")
        
        return execution_id
    
    def execute_action(self, execution_id: str) -> bool:
        """Execute an action"""
        execution = self.executions.get(execution_id)
        if not execution:
            self.logger.error(f"Execution {execution_id} not found")
            return False
        
        action = self.registered_actions.get(execution.action_name)
        if not action:
            execution.status = ActionStatus.FAILED
            execution.error_message = f"Action {execution.action_name} not found"
            return False
        
        try:
            execution.status = ActionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            
            context = ActionExecutionContext(execution, self.core, execution.executed_by)
            
            # Execute the action
            result = action.execute(execution.population_target, execution.parameters, context)
            
            # Update execution
            execution.status = ActionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.result = result
            execution.progress = 100.0
            
            self.logger.info(f"Execution {execution_id} completed successfully")
            return True
            
        except Exception as e:
            execution.status = ActionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(e)
            
            self.logger.error(f"Execution {execution_id} failed: {e}")
            return False
    
    def get_execution(self, execution_id: str) -> Optional[ActionExecution]:
        """Get execution details"""
        return self.executions.get(execution_id)
    
    def list_executions(self, action_name: Optional[str] = None, 
                       status: Optional[ActionStatus] = None,
                       user_id: Optional[str] = None) -> List[ActionExecution]:
        """List executions with optional filtering"""
        executions = list(self.executions.values())
        
        if action_name:
            executions = [e for e in executions if e.action_name == action_name]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        if user_id:
            executions = [e for e in executions if e.executed_by == user_id]
        
        return sorted(executions, key=lambda e: e.created_at, reverse=True)
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution"""
        execution = self.executions.get(execution_id)
        if not execution:
            return False
        
        if execution.status == ActionStatus.RUNNING:
            execution.status = ActionStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            self.logger.info(f"Cancelled execution {execution_id}")
            return True
        
        return False
    
    def get_action_catalog(self) -> Dict[str, Any]:
        """Get complete catalog of available actions"""
        catalog = {}
        
        for action_type in ActionType:
            catalog[action_type.value] = {
                "actions": [
                    action.get_info() 
                    for action in self.registered_actions.values()
                    if action.action_type == action_type
                ],
                "count": len([
                    action for action in self.registered_actions.values()
                    if action.action_type == action_type
                ])
            }
        
        return catalog