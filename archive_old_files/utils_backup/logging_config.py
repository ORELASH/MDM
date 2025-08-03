"""
Advanced Logging Configuration for RedshiftManager
Development-friendly logging with detailed debugging capabilities.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import traceback


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Format the message
        formatted = super().format(record)
        
        # Reset levelname for other formatters
        record.levelname = levelname
        
        return formatted


class DevelopmentLogger:
    """Enhanced logger for development with debugging capabilities"""
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Add handlers
        self._setup_console_handler()
        self._setup_file_handler()
        self._setup_debug_handler()
        self._setup_error_handler()
    
    def _setup_console_handler(self):
        """Setup colored console handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self):
        """Setup rotating file handler for all logs"""
        log_file = self.log_dir / f"{self.name}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def _setup_debug_handler(self):
        """Setup debug handler for detailed debugging"""
        debug_file = self.log_dir / f"{self.name}_debug.log"
        
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_file, maxBytes=50*1024*1024, backupCount=3
        )
        debug_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
        )
        debug_handler.setFormatter(formatter)
        
        self.logger.addHandler(debug_handler)
    
    def _setup_error_handler(self):
        """Setup error handler for errors and critical issues"""
        error_file = self.log_dir / f"{self.name}_errors.log"
        
        error_handler = logging.handlers.RotatingFileHandler(
            error_file, maxBytes=10*1024*1024, backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d\n'
            'Function: %(funcName)s\n'
            'Message: %(message)s\n'
            '%(pathname)s\n'
            '---\n'
        )
        error_handler.setFormatter(formatter)
        
        self.logger.addHandler(error_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger"""
        return self.logger


class DevLogger:
    """Development logger with enhanced debugging capabilities"""
    
    def __init__(self, name: str):
        self.dev_logger = DevelopmentLogger(name)
        self.logger = self.dev_logger.get_logger()
    
    def debug(self, message: str, **kwargs):
        """Enhanced debug logging"""
        extra_info = self._get_extra_info(**kwargs)
        self.logger.debug(f"{message} {extra_info}")
    
    def info(self, message: str, **kwargs):
        """Enhanced info logging"""
        extra_info = self._get_extra_info(**kwargs)
        self.logger.info(f"{message} {extra_info}")
    
    def warning(self, message: str, **kwargs):
        """Enhanced warning logging"""
        extra_info = self._get_extra_info(**kwargs)
        self.logger.warning(f"{message} {extra_info}")
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Enhanced error logging with exception details"""
        extra_info = self._get_extra_info(**kwargs)
        
        if exception:
            error_details = self._format_exception(exception)
            self.logger.error(f"{message} {extra_info}\nException: {error_details}")
        else:
            self.logger.error(f"{message} {extra_info}")
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Enhanced critical logging"""
        extra_info = self._get_extra_info(**kwargs)
        
        if exception:
            error_details = self._format_exception(exception)
            self.logger.critical(f"{message} {extra_info}\nException: {error_details}")
        else:
            self.logger.critical(f"{message} {extra_info}")
    
    def function_entry(self, func_name: str, **kwargs):
        """Log function entry with parameters"""
        params = json.dumps(kwargs, default=str, indent=2) if kwargs else "No parameters"
        self.logger.debug(f"🔵 ENTER {func_name} - Params: {params}")
    
    def function_exit(self, func_name: str, result: Any = None, **kwargs):
        """Log function exit with result"""
        result_str = json.dumps(result, default=str, indent=2) if result is not None else "No return value"
        extra_info = self._get_extra_info(**kwargs)
        self.logger.debug(f"🔴 EXIT {func_name} - Result: {result_str} {extra_info}")
    
    def performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics"""
        extra_info = self._get_extra_info(**kwargs)
        self.logger.info(f"⚡ PERF {operation} - Duration: {duration:.4f}s {extra_info}")
    
    def database_query(self, query: str, params: Dict = None, duration: float = None):
        """Log database queries"""
        params_str = json.dumps(params, default=str) if params else "No params"
        duration_str = f" - Duration: {duration:.4f}s" if duration else ""
        self.logger.debug(f"🗄️  DB QUERY{duration_str}\nSQL: {query}\nParams: {params_str}")
    
    def api_call(self, method: str, url: str, status_code: int = None, duration: float = None):
        """Log API calls"""
        status_str = f" - Status: {status_code}" if status_code else ""
        duration_str = f" - Duration: {duration:.4f}s" if duration else ""
        self.logger.info(f"🌐 API {method} {url}{status_str}{duration_str}")
    
    def user_action(self, user_id: str, action: str, details: Dict = None):
        """Log user actions for audit"""
        details_str = json.dumps(details, default=str) if details else "No details"
        self.logger.info(f"👤 USER ACTION - User: {user_id} - Action: {action} - Details: {details_str}")
    
    def system_event(self, event_type: str, details: Dict = None):
        """Log system events"""
        details_str = json.dumps(details, default=str) if details else "No details"
        self.logger.info(f"🔧 SYSTEM EVENT - Type: {event_type} - Details: {details_str}")
    
    def _get_extra_info(self, **kwargs) -> str:
        """Get extra information from kwargs"""
        if not kwargs:
            return ""
        
        # Filter out None values
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        if not filtered_kwargs:
            return ""
        
        try:
            return f"- Extra: {json.dumps(filtered_kwargs, default=str)}"
        except Exception:
            return f"- Extra: {str(filtered_kwargs)}"
    
    def _format_exception(self, exception: Exception) -> str:
        """Format exception with full traceback"""
        return f"{type(exception).__name__}: {str(exception)}\nTraceback:\n{traceback.format_exc()}"


def get_dev_logger(name: str) -> DevLogger:
    """Get a development logger instance"""
    return DevLogger(name)


def setup_global_logging(log_level: str = "DEBUG"):
    """Setup global logging configuration"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set global log level
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    
    # Create global logger
    global_logger = get_dev_logger("redshift_manager")
    
    # Log system startup
    global_logger.system_event("application_startup", {
        "timestamp": datetime.now().isoformat(),
        "log_level": log_level,
        "python_version": sys.version,
        "working_directory": os.getcwd()
    })
    
    return global_logger


# Context manager for function logging
class log_function:
    """Decorator/context manager for function logging"""
    
    def __init__(self, logger: DevLogger, func_name: str = None):
        self.logger = logger
        self.func_name = func_name
    
    def __call__(self, func):
        """Use as decorator"""
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = self.func_name or func.__name__
            
            # Log entry
            self.logger.function_entry(func_name, args=args, kwargs=kwargs)
            
            try:
                # Execute function
                import time
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log exit
                self.logger.function_exit(func_name, result=result)
                self.logger.performance(func_name, duration)
                
                return result
                
            except Exception as e:
                self.logger.error(f"Function {func_name} failed", exception=e)
                raise
        
        return wrapper
    
    def __enter__(self):
        """Use as context manager"""
        if self.func_name:
            self.logger.function_entry(self.func_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        if exc_type:
            self.logger.error(f"Context {self.func_name} failed", exception=exc_val)
        elif self.func_name:
            self.logger.function_exit(self.func_name)


# Global logger instance
_global_logger = None

def get_logger(name: str = None) -> DevLogger:
    """Get global logger or create named logger"""
    global _global_logger
    
    if name:
        return get_dev_logger(name)
    
    if _global_logger is None:
        _global_logger = setup_global_logging()
    
    return _global_logger


if __name__ == "__main__":
    # Test the logging system
    logger = get_logger("test")
    
    logger.info("Testing logging system")
    logger.debug("Debug message", test_param="test_value")
    logger.warning("Warning message", user_id="test_user")
    
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.error("Test error", exception=e)
    
    logger.performance("test_operation", 0.123, items_processed=100)
    logger.database_query("SELECT * FROM test", {"id": 1}, 0.045)
    logger.user_action("user123", "login", {"ip": "192.168.1.1"})
    
    print("✅ Logging system test completed - check logs/ directory")