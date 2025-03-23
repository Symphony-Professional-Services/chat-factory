"""
Factory for creating datetime strategy instances.
"""

import logging
from typing import Optional

from ...config.base_config import BaseConfig
from ..base.datetime_strategy import DatetimeStrategy
from .business_hours_strategy import BusinessHoursDatetimeStrategy
from .uniform_distribution_strategy import UniformDistributionStrategy
from .custom_period_strategy import CustomPeriodStrategy


def create_datetime_strategy(config: BaseConfig) -> Optional[DatetimeStrategy]:
    """
    Create a datetime strategy based on configuration.
    
    Args:
        config: Configuration settings
        
    Returns:
        DatetimeStrategy instance or None if not configured
    """
    # Check if datetime distribution is enabled
    datetime_enabled = getattr(config, 'DATETIME_DISTRIBUTION_ENABLED', False)
    
    if not datetime_enabled:
        logging.info("Datetime distribution is disabled in configuration")
        return None
    
    # Get strategy type from config
    strategy_type = getattr(config, 'DATETIME_STRATEGY', 'business_hours')
    
    logging.info(f"Creating datetime strategy of type: {strategy_type}")
    
    if strategy_type == 'business_hours':
        return BusinessHoursDatetimeStrategy(config)
    elif strategy_type == 'uniform':
        return UniformDistributionStrategy(config)
    elif strategy_type == 'custom_period':
        return CustomPeriodStrategy(config)
    else:
        logging.warning(f"Unknown datetime strategy type: {strategy_type}, defaulting to business_hours")
        return BusinessHoursDatetimeStrategy(config)