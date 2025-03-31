"""Utility functions for Chat Factory."""

import os
import re
import logging
import chat_factory.utils.batch_logging as batch_logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from .batch_logging import SummaryStatisticsLogger



def sanitize_filename(name: str) -> str:
    """
    Removes or replaces characters that are invalid in filenames.
    
    Args:
        name: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    return re.sub(r'[<>:"/\\|?*]', '', name)


def setup_logging(log_file: str, run_id: Optional[str] = None) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        log_file: Path to the log file
        run_id: Optional run ID to include in the log file name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("chat_factory")
    logger.setLevel(batch_logging.DEBUG)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Add run_id to log file name if provided
    if run_id:
        log_file_path = Path(log_file)
        log_file = str(log_file_path.parent / f"{log_file_path.stem}_{run_id}{log_file_path.suffix}")
    
    # Create file handler
    file_handler = batch_logging.FileHandler(log_file)
    file_handler.setLevel(batch_logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = batch_logging.StreamHandler()
    console_handler.setLevel(batch_logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def ensure_directory(directory_path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        The directory path
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)