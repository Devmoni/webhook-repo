import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    logger = logging.getLogger('webhook')
    logger.setLevel(logging.INFO)
    
    # Create handlers
    file_handler = RotatingFileHandler('logs/webhook.log', maxBytes=10240, backupCount=10)
    console_handler = logging.StreamHandler()
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(log_format)
    console_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Create logger instance
logger = setup_logger() 