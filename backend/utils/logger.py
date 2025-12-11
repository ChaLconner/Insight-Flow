import logging
import os
from typing import Optional

import json

class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add source info if in debug or error
        if record.levelno >= logging.ERROR or os.getenv("DEBUG", "false").lower() == "true":
            log_record.update({
                "filename": record.filename,
                "lineno": record.lineno,
                "funcName": record.funcName
            })
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Setup logger with appropriate configuration based on environment.
    
    Args:
        name: Logger name
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level based on environment or parameter
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        # Use DEBUG in development, INFO in production
        log_level = logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO
    
    logger.setLevel(log_level)
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatter
    if os.getenv("ENVIRONMENT") == "production":
        # Use JSON formatter for production
        formatter = JsonFormatter()
    elif os.getenv("DEBUG", "false").lower() == "true":
        # Detailed format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
    else:
        # Simple format for other environments (e.g. testing)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Create default logger for application
app_logger = setup_logger("insight_flow")

# Create a default logger for general use
logger = setup_logger("insight_flow")