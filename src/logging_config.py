"""
Structured Logging Configuration for Photo Search Application

This module provides:
1. Centralized logging configuration
2. Structured logging with JSON format
3. Different log levels for different environments
4. Log rotation and archival
5. Performance monitoring integration
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import os


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in log_entry and key not in ['name', 'msg', 'args', 'levelname',
                                                   'levelno', 'pathname', 'filename',
                                                   'module', 'lineno', 'funcName',
                                                   'created', 'msecs', 'relativeCreated',
                                                   'thread', 'threadName', 'processName',
                                                   'process', 'getMessage', 'exc_info',
                                                   'exc_text', 'stack_info']:
                log_entry[key] = value

        return json.dumps(log_entry)


class PhotoSearchLogger:
    """Centralized logging system for the photo search application."""

    def __init__(self, name: str = "PhotoSearch", log_level: str = "INFO",
                 log_file: Optional[str] = None, enable_console: bool = True):
        """
        Initialize the logger.

        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for logging
            enable_console: Whether to log to console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Prevent duplicate handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Create formatters
        json_formatter = JSONFormatter()

        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(json_formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Use RotatingFileHandler for log rotation
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(json_formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        """Return the configured logger."""
        return self.logger


class PerformanceTracker:
    """Track performance metrics for key operations."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics = {}

    def measure(self, operation_name: str):
        """Decorator to measure execution time of functions."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = datetime.now()
                try:
                    result = func(*args, **kwargs)
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000  # in ms

                    # Log performance metric
                    self.logger.info(
                        f"Performance metric: {operation_name}",
                        extra={
                            'operation': operation_name,
                            'execution_time_ms': round(execution_time, 2),
                            'status': 'success'
                        }
                    )

                    return result
                except Exception as e:
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000  # in ms
                    self.logger.error(
                        f"Performance metric: {operation_name}",
                        extra={
                            'operation': operation_name,
                            'execution_time_ms': round(execution_time, 2),
                            'status': 'error',
                            'error': str(e)
                        }
                    )
                    raise
            return wrapper
        return decorator

    def log_custom_metric(self, operation_name: str, value: float, unit: str = "ms"):
        """Log a custom performance metric."""
        self.logger.info(
            f"Custom metric: {operation_name}",
            extra={
                'operation': operation_name,
                'value': value,
                'unit': unit
            }
        )


# Global logger instance
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> tuple:
    """
    Setup logging for the application.

    Args:
        log_level: Logging level
        log_file: Optional file path for logging

    Returns:
        Tuple of (logger, performance_tracker)
    """
    # Use environment variable for log file if not provided
    if not log_file:
        log_file = os.getenv("PHOTO_SEARCH_LOG_FILE", "logs/app.log")

    # Create logger
    ps_logger = PhotoSearchLogger(
        name="PhotoSearch",
        log_level=log_level,
        log_file=log_file,
        enable_console=True
    )

    logger = ps_logger.get_logger()

    # Create performance tracker
    perf_tracker = PerformanceTracker(logger)

    return logger, perf_tracker


# Usage example functions
def log_search_operation(
    logger: logging.Logger,
    query: str,
    mode: str,
    results_count: int,
    execution_time: float,
    user_agent: str = "unknown"
):
    """Log a search operation with structured details."""
    logger.info(
        "Search operation completed",
        extra={
            'operation': 'search',
            'query': query,
            'mode': mode,
            'results_count': results_count,
            'execution_time_ms': execution_time,
            'user_agent': user_agent
        }
    )


def log_indexing_operation(
    logger: logging.Logger,
    directory: str,
    files_processed: int,
    execution_time: float,
    errors: int = 0
):
    """Log an indexing operation with structured details."""
    logger.info(
        "Indexing operation completed",
        extra={
            'operation': 'indexing',
            'directory': directory,
            'files_processed': files_processed,
            'execution_time_ms': execution_time,
            'errors': errors
        }
    )


def log_error(
    logger: logging.Logger,
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None
):
    """Log an error with structured details."""
    extra_data = {
        'error_type': error_type,
        'error_message': error_message
    }

    if context:
        extra_data.update(context)

    logger.error(
        f"Error occurred: {error_type}",
        extra=extra_data
    )
