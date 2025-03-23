"""
Utilities for loading configurations from various sources.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any

from .base_config import BaseConfig


def load_config_from_file(file_path: str) -> BaseConfig:
    """
    Load configuration from a Python file.
    
    Args:
        file_path: Path to the Python file containing configuration
        
    Returns:
        BaseConfig instance with values from the file
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    # Create a unique module name
    module_name = f"_chat_factory_config_{file_path.stem}"
    
    # Load the module
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    config_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = config_module
    spec.loader.exec_module(config_module)
    
    # Extract configuration values (uppercase variables)
    config_dict = {
        key: value for key, value in vars(config_module).items() 
        if not key.startswith('__') and key.isupper()
    }
    
    # Create and return a BaseConfig instance
    return BaseConfig(**config_dict)