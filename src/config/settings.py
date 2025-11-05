import os
from typing import Dict, Any

class AppConfig:
    """
    Centralized application configuration
    """
    
    def __init__(self):
        # Performance monitoring settings
        self.ENABLE_PERFORMANCE_MONITORING = self._get_bool_env(
            'ENABLE_PERFORMANCE_MONITORING', 
            default=True  # Default to enabled for development
        )
        
        # Performance thresholds
        self.SLOW_QUERY_THRESHOLD = self._get_float_env(
            'SLOW_QUERY_THRESHOLD', 
            default=3.0  # seconds
        )
        
        self.SLOW_OPERATION_THRESHOLD = self._get_float_env(
            'SLOW_OPERATION_THRESHOLD', 
            default=5.0  # seconds
        )
        
        self.SLOW_CHART_THRESHOLD = self._get_float_env(
            'SLOW_CHART_THRESHOLD', 
            default=2.0  # seconds
        )
        
        # Environment detection
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
        self.IS_PRODUCTION = self.ENVIRONMENT == 'production'
        self.IS_DEVELOPMENT = self.ENVIRONMENT == 'development'
        
        # Logging configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.ENABLE_FILE_LOGGING = self._get_bool_env('ENABLE_FILE_LOGGING', default=False)
        
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable with fallback"""
        value = os.getenv(key, '').lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        return default
    
    def _get_float_env(self, key: str, default: float) -> float:
        """Get float environment variable with fallback"""
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get all performance-related configuration"""
        return {
            'enabled': self.ENABLE_PERFORMANCE_MONITORING,
            'query_threshold': self.SLOW_QUERY_THRESHOLD,
            'operation_threshold': self.SLOW_OPERATION_THRESHOLD,
            'chart_threshold': self.SLOW_CHART_THRESHOLD,
            'environment': self.ENVIRONMENT
        }

# Global configuration instance
config = AppConfig()