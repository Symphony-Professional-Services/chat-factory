"""
Uniform datetime distribution strategy.

This strategy generates timestamps that are evenly distributed across time periods.
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from ..base.datetime_strategy import DatetimeStrategy


class UniformDistributionStrategy(DatetimeStrategy):
    """
    Datetime strategy that uniformly distributes conversations across time periods.
    
    This strategy is useful for testing or when no specific time distribution is needed.
    It creates an even distribution of conversations across days and hours.
    """
    
    def __init__(self, config):
        """
        Initialize the uniform distribution datetime strategy.
        
        Args:
            config: Configuration with settings for time distribution
        """
        super().__init__(config)
        
        # Default settings if not specified in config
        self.start_date = getattr(config, 'START_DATE', datetime.now().isoformat())
        self.end_date = getattr(config, 'END_DATE', 
                               (datetime.now() + timedelta(days=30)).isoformat())
                               
        # Message delay settings in seconds
        self.message_delay_mean = getattr(config, 'MESSAGE_DELAY_MEAN', 60)     # 1 minute
        self.message_delay_std_dev = getattr(config, 'MESSAGE_DELAY_STD_DEV', 30)  # 30 seconds
        
        logging.info(f"Uniform distribution strategy initialized with date range: {self.start_date} to {self.end_date}")
    
    def generate_conversation_timestamp(self, conversation_number: int) -> str:
        """
        Generate a timestamp uniformly distributed across the date range.
        
        Args:
            conversation_number: Sequence number for this conversation
            
        Returns:
            ISO format timestamp string
        """
        start_dt, end_dt = self.parse_date_range(self.start_date, self.end_date)
        
        # Check if we have specific distribution already calculated
        if hasattr(self, '_distribution_dates') and self._distribution_dates:
            if conversation_number < len(self._distribution_dates):
                # Use pre-calculated date
                date_str = self._distribution_dates[conversation_number]
                base_date = datetime.fromisoformat(date_str + 'T00:00:00')
                
                # Add random time of day
                random_seconds_in_day = random.randint(0, 86399)  # Seconds in a day (24*60*60)-1
                random_dt = base_date + timedelta(seconds=random_seconds_in_day)
                
                # Ensure it's within our time range
                if random_dt < start_dt:
                    random_dt = start_dt
                elif random_dt > end_dt:
                    random_dt = end_dt
                    
                return random_dt.isoformat()
            else:
                logging.warning(f"Conversation number {conversation_number} exceeds pre-calculated distribution size " +
                               f"({len(self._distribution_dates)}). Using random time within range.")
        
        # No distribution calculated yet or conversation_number out of range
        # Generate a random timestamp within the range
        range_seconds = int((end_dt - start_dt).total_seconds())
        random_seconds = random.randint(0, range_seconds)
        random_dt = start_dt + timedelta(seconds=random_seconds)
        
        return random_dt.isoformat()
    
    def generate_message_timestamps(self, 
                                  conversation_timestamp: str,
                                  num_messages: int) -> List[str]:
        """
        Generate timestamps for each message in a conversation with uniform delays.
        
        Args:
            conversation_timestamp: Timestamp for the start of conversation
            num_messages: Number of messages to generate timestamps for
            
        Returns:
            List of ISO format timestamp strings
        """
        if num_messages <= 0:
            return []
            
        start_dt = datetime.fromisoformat(conversation_timestamp)
        timestamps = [start_dt]
        
        # Generate timestamps with uniform delays
        current_dt = start_dt
        for i in range(1, num_messages):
            # Add a random delay between messages
            delay_seconds = max(
                5,  # Minimum 5 second delay
                random.normalvariate(
                    self.message_delay_mean,
                    self.message_delay_std_dev
                )
            )
                
            current_dt = current_dt + timedelta(seconds=delay_seconds)
            timestamps.append(current_dt)
        
        return [dt.isoformat() for dt in timestamps]
    
    def get_message_count_distribution(self, 
                                      time_period: Tuple[str, str], 
                                      total_conversations: int) -> Dict[str, int]:
        """
        Get uniform distribution of conversations across a time period.
        
        Args:
            time_period: Tuple of (start_date, end_date) as ISO format strings
            total_conversations: Total number of conversations to distribute
            
        Returns:
            Dictionary mapping dates to conversation counts
        """
        start_dt, end_dt = self.parse_date_range(time_period[0], time_period[1])
        
        # Calculate number of days in period
        days_in_period = (end_dt - start_dt).days + 1
        
        # Initialize distribution with zeros for all dates
        distribution = {}
        current_dt = start_dt
        while current_dt <= end_dt:
            distribution[current_dt.date().isoformat()] = 0
            current_dt = current_dt + timedelta(days=1)
        
        # Distribute conversations evenly
        base_count = total_conversations // days_in_period
        extra = total_conversations % days_in_period
        
        # Assign base count to all days
        for day in distribution:
            distribution[day] = base_count
        
        # Distribute remaining conversations randomly
        days = list(distribution.keys())
        random.shuffle(days)
        for i in range(extra):
            distribution[days[i]] += 1
                
        return distribution