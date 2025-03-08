import logging
import sys
import os
from datetime import datetime

def setup_logger(name=None, log_file=None, level=logging.INFO):
    """
    Configure a logger with file and console handlers
    
    Args:
        name (str): Logger name (optional)
        log_file (str): Path to log file (optional)
        level (int): Logging level
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file specified
    if log_file:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.dirname(log_file)
        if logs_dir and not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_command_logger():
    """
    Get a logger for command processing that logs to a daily file
    
    Returns:
        logging.Logger: Logger for command processing
    """
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = f"logs/commands_{today}.log"
    return setup_logger('command_processor', log_file)

def get_api_logger():
    """
    Get a logger for API requests that logs to a daily file
    
    Returns:
        logging.Logger: Logger for API requests
    """
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = f"logs/api_{today}.log"
    return setup_logger('api', log_file)

def get_wp_logger():
    """
    Get a logger for WordPress operations that logs to a daily file
    
    Returns:
        logging.Logger: Logger for WordPress operations
    """
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = f"logs/wordpress_{today}.log"
    return setup_logger('wordpress', log_file)