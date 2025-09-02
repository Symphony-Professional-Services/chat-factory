"""Configuration management for Chat Factory."""

from .base_config import BaseConfig
from .config_loader import load_config_from_file

__all__ = ['BaseConfig', 'load_config_from_file']