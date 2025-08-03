"""
RedshiftManager Core Module System
Advanced modular architecture for dynamic functionality and cross-system portability.
"""

from .module_registry import ModuleRegistry
from .module_loader import ModuleLoader
from .plugin_interface import PluginInterface, ModuleBase
from .action_framework import ActionFramework, Action
from .population_manager import PopulationManager

__version__ = "1.0.0"
__all__ = [
    'ModuleRegistry',
    'ModuleLoader', 
    'PluginInterface',
    'ModuleBase',
    'ActionFramework',
    'Action',
    'PopulationManager'
]