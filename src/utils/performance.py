import time
from functools import wraps
import logging
from typing import Any, Callable, Optional

# Import configuration
from src.config.settings import config

def monitor_performance(func_name: str = "Unknown"):
    """
    Decorator to monitor function performance and log execution times
    Can be disabled via configuration
    
    Usage:
        @monitor_performance("My Function Name")
        def my_function():
            # function code here
            
    Args:
        func_name (str): Custom name for the function being monitored
        
    Returns:
        Decorated function with performance monitoring (or passthrough if disabled)
    """
    def decorator(func: Callable) -> Callable:
        # If performance monitoring is disabled, return the original function
        if not config.ENABLE_PERFORMANCE_MONITORING:
            return func
            
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log performance info
                print(f"⏱️ {func_name} completed in {duration:.2f} seconds")
                
                # Log slow operations based on threshold
                if duration > config.SLOW_OPERATION_THRESHOLD:
                    message = f"Slow operation detected: {func_name} took {duration:.2f} seconds"
                    print(f"⚠️ {message}")
                    if config.ENABLE_FILE_LOGGING:
                        logging.warning(message)
                        
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                error_msg = f"{func_name} failed after {duration:.2f} seconds: {str(e)}"
                print(f"❌ {error_msg}")
                
                # Always log errors regardless of monitoring setting
                if config.ENABLE_FILE_LOGGING:
                    logging.error(f"Performance monitor caught error: {error_msg}")
                    
                raise
                
        return wrapper
    return decorator

def monitor_query_performance(query_name: str = "Unknown Query"):
    """
    Specialized decorator for database query performance monitoring
    Can be disabled via configuration
    
    Usage:
        @monitor_query_performance("User Engagement Query")
        def get_user_data():
            # database query code here
    """
    def decorator(func: Callable) -> Callable:
        # If performance monitoring is disabled, return the original function
        if not config.ENABLE_PERFORMANCE_MONITORING:
            return func
            
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Enhanced logging for queries with record counts
                record_info = ""
                if hasattr(result, '__len__'):
                    try:
                        record_count = len(result)
                        record_info = f" ({record_count} records)"
                    except:
                        record_info = ""
                elif isinstance(result, dict):
                    try:
                        total_records = sum(len(v) if hasattr(v, '__len__') else 0 for v in result.values())
                        record_info = f" ({total_records} total records)"
                    except:
                        record_info = ""
                
                print(f"🗃️ {query_name} completed in {duration:.2f} seconds{record_info}")
                
                # Log slow queries based on threshold
                if duration > config.SLOW_QUERY_THRESHOLD:
                    message = f"Slow query detected: {query_name} took {duration:.2f} seconds{record_info}"
                    print(f"⚠️ {message}")
                    if config.ENABLE_FILE_LOGGING:
                        logging.warning(message)
                        
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                error_msg = f"{query_name} failed after {duration:.2f} seconds: {str(e)}"
                print(f"❌ {error_msg}")
                
                # Always log errors
                if config.ENABLE_FILE_LOGGING:
                    logging.error(f"Query performance monitor caught error: {error_msg}")
                    
                raise
                
        return wrapper
    return decorator

def monitor_chart_performance(chart_name: str = "Unknown Chart"):
    """
    Specialized decorator for chart generation performance monitoring
    Can be disabled via configuration
    
    Usage:
        @monitor_chart_performance("Engagement Trends Chart")
        def create_engagement_chart():
            # chart creation code here
    """
    def decorator(func: Callable) -> Callable:
        # If performance monitoring is disabled, return the original function
        if not config.ENABLE_PERFORMANCE_MONITORING:
            return func
            
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                print(f"📊 {chart_name} rendered in {duration:.2f} seconds")
                
                # Log slow chart operations based on threshold
                if duration > config.SLOW_CHART_THRESHOLD:
                    message = f"Slow chart rendering: {chart_name} took {duration:.2f} seconds"
                    print(f"⚠️ {message}")
                    if config.ENABLE_FILE_LOGGING:
                        logging.warning(message)
                        
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                error_msg = f"{chart_name} failed after {duration:.2f} seconds: {str(e)}"
                print(f"❌ {error_msg}")
                
                # Always log errors
                if config.ENABLE_FILE_LOGGING:
                    logging.error(f"Chart performance monitor caught error: {error_msg}")
                    
                raise
                
        return wrapper
    return decorator

# Utility functions for runtime control
def is_monitoring_enabled() -> bool:
    """Check if performance monitoring is currently enabled"""
    return config.ENABLE_PERFORMANCE_MONITORING

def get_monitoring_config() -> dict:
    """Get current monitoring configuration"""
    return config.get_performance_config()

def log_performance_info(message: str, level: str = "info"):
    """Manual performance logging utility"""
    if not config.ENABLE_PERFORMANCE_MONITORING:
        return
        
    print(f"📈 {message}")
    
    if config.ENABLE_FILE_LOGGING:
        if level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)
        else:
            logging.info(message)