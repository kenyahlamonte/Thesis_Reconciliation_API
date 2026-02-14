"""
Simple logging configuration for the reconciliation API.

Provides easy-to-read console output for development and debugging.
"""

import logging
import sys

# Color codes for console output (makes logs easier to read)
class LogColors:
    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""
    
    COLORS = {
        logging.DEBUG: LogColors.GRAY,
        logging.INFO: LogColors.BLUE,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.RED,
    }
    
    def format(self, record: logging.LogRecord):
        # Add color to the level name
        levelname = record.levelname
        if record.levelno in self.COLORS:
            levelname_color = f"{self.COLORS[record.levelno]}{levelname}{LogColors.RESET}"
            record.levelname = levelname_color
        
        # Format the message
        result = super().format(record)
        
        # Reset levelname for next use
        record.levelname = levelname
        
        return result


def setup_logging(level: str = "INFO", use_colors: bool = True) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_colors: Whether to use colored output (disable for file logging)
    
    Example:
        >>> setup_logging("DEBUG")  # Show all logs
        >>> setup_logging("INFO")   # Normal operation
        >>> setup_logging("ERROR")  # Only errors
    """
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Set up formatter
    if use_colors:
        formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add our handler
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Usually __name__ of the module
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting reconciliation")
    """
    return logging.getLogger(name)


# Simple convenience function for quick logging setup
def init_logging(debug: bool = False) -> None:
    """
    Quick logging initialization.
    
    Args:
        debug: If True, enables DEBUG level logging
        
    Example:
        >>> init_logging(debug=True)  # Verbose logging
        >>> init_logging()             # Normal logging
    """
    level = "DEBUG" if debug else "INFO"
    setup_logging(level=level)