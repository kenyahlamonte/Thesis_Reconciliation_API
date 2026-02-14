"""
Simple logging configuration for the reconciliation API.

Provides easy-to-read console output for development and debugging.
"""

import logging
import sys

#colour codes for console output
class LogColours:
    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    GRAY = "\033[90m"


class ColouredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""
    
    COLOURS = {
        logging.DEBUG: LogColours.GRAY,
        logging.INFO: LogColours.BLUE,
        logging.WARNING: LogColours.YELLOW,
        logging.ERROR: LogColours.RED,
        logging.CRITICAL: LogColours.RED,
    }
    
    def format(self, record: logging.LogRecord):
        #add color to the level name
        levelname = record.levelname
        if record.levelno in self.COLOURS:
            levelname_color = f"{self.COLOURS[record.levelno]}{levelname}{LogColours.RESET}"
            record.levelname = levelname_color
        
        #format the message
        result = super().format(record)
        
        #reset levelname for next use
        record.levelname = levelname
        
        return result


def setup_logging(level: str = "INFO", use_colours: bool = True) -> None:
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
    #convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    #create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    
    #set up formatter
    if use_colours:
        formatter = ColouredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    
    #configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    #remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    #add handler
    root_logger.addHandler(console_handler)
    
    #reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[console_handler],
        force=True  #override existing config (uvicorn, etc.)
    )

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

#simple convenience function for quick logging setup
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