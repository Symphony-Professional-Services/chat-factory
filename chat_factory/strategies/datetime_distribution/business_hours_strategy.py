"""
Business hours datetime distribution strategy.

This strategy generates timestamps that are weighted toward business hours and workdays.
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from ..base.datetime_strategy import DatetimeStrategy


class BusinessHoursDatetimeStrategy(DatetimeStrategy):
    """
    Datetime strategy that weights conversations toward business hours and workdays.
    
    This strategy generates timestamps that follow typical business patterns:
    - More conversations during weekdays (Mon-Fri) than weekends
    - More conversations during business hours (e.g., 9am-5pm)
    - Realistic delays between messages in a conversation
    """
    
    def __init__(self, config):
        """
        Initialize the business hours datetime strategy.
        
        Args:
            config: Configuration with settings for time distribution
        """
        super().__init__(config)
        
        # Default settings if not specified in config
        self.start_date = getattr(config, 'START_DATE', datetime.now().isoformat())
        self.end_date = getattr(config, 'END_DATE', 
                               (datetime.now() + timedelta(days=30)).isoformat())
        
        self.business_hours_start = getattr(config, 'BUSINESS_HOURS_START', 9)  # 9 AM
        self.business_hours_end = getattr(config, 'BUSINESS_HOURS_END', 17)     # 5 PM
        
        # Default weekday distribution: 80% on weekdays, 20% on weekends
        self.weekend_weight = getattr(config, 'WEEKEND_WEIGHT', 0.2)
        
        # Default weights for different days of the week (for weekdays)
        self.weekday_weights = getattr(config, 'WEEKDAY_WEIGHTS', {
            'Monday': 0.25,
            'Tuesday': 0.2,
            'Wednesday': 0.2,
            'Thursday': 0.2,
            'Friday': 0.15
        })
        
        # Default weights for different times of day
        self.hour_weights = getattr(config, 'HOUR_WEIGHTS', {
            'morning': 0.3,     # 9am-12pm
            'afternoon': 0.5,   # 12pm-5pm
            'evening': 0.2      # 5pm-8pm
        })
        
        # Message delay settings in seconds
        self.message_delay_mean = getattr(config, 'MESSAGE_DELAY_MEAN', 60)     # 1 minute
        self.message_delay_std_dev = getattr(config, 'MESSAGE_DELAY_STD_DEV', 30)  # 30 seconds
        
        logging.info(f"Business hours strategy initialized with date range: {self.start_date} to {self.end_date}")
    
    def generate_conversation_timestamp(self, conversation_number: int) -> str:
        """
        Generate a timestamp for a conversation weighted toward business hours.
        
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
                logging.debug(f"Using pre-calculated date {date_str} for conversation {conversation_number}")
                random_date = datetime.fromisoformat(date_str + 'T00:00:00')
                is_weekend = random_date.weekday() >= 5  # 5=Saturday, 6=Sunday
            else:
                # Fall back to standard algorithm
                logging.warning(f"Conversation number {conversation_number} exceeds pre-calculated distribution" +
                                f" size ({len(self._distribution_dates)}). Using weighted random date.")
                is_weekend = random.random() < self.weekend_weight
                range_days = (end_dt - start_dt).days
                if range_days <= 0:
                    range_days = 1  # Ensure at least 1 day range
                random_day = random.randint(0, range_days)
                random_date = start_dt + timedelta(days=random_day)
        else:
            # Determine if this conversation will be on a weekend
            is_weekend = random.random() < self.weekend_weight
            
            # Generate a random date within the range
            range_days = (end_dt - start_dt).days
            if range_days <= 0:
                range_days = 1  # Ensure at least 1 day range
                
            random_day = random.randint(0, range_days)
            random_date = start_dt + timedelta(days=random_day)
        
        # If it's supposed to be a weekend, but we got a weekday, adjust
        day_of_week = random_date.weekday()  # 0=Monday, 6=Sunday
        if is_weekend and day_of_week < 5:  # It's a weekday but we want a weekend
            # Find closest weekend day
            days_to_saturday = (5 - day_of_week) % 7
            days_to_sunday = (6 - day_of_week) % 7
            
            # Choose Saturday or Sunday randomly
            weekend_offset = days_to_saturday if random.random() < 0.5 else days_to_sunday
            random_date = random_date + timedelta(days=weekend_offset)
            
        elif not is_weekend and day_of_week >= 5:  # It's a weekend but we want a weekday
            # Determine which day of the week to use based on weights
            weekday_names = list(self.weekday_weights.keys())
            weekday_probs = list(self.weekday_weights.values())
            target_day_name = random.choices(weekday_names, weights=weekday_probs, k=1)[0]
            
            # Map day name to day number
            day_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4}
            target_day_num = day_map[target_day_name]
            
            # Calculate offset to reach the target day
            # First, go back to Monday of current week
            days_since_monday = day_of_week - 0 if day_of_week >= 0 else 7 + day_of_week
            monday_date = random_date - timedelta(days=days_since_monday)
            
            # Then go forward to target day
            random_date = monday_date + timedelta(days=target_day_num)
            
            # Adjust if we went outside our date range
            if random_date < start_dt:
                random_date = start_dt + timedelta(days=target_day_num)
            elif random_date > end_dt:
                random_date = end_dt - timedelta(days=(6 - target_day_num))
        
        # Now determine the time of day based on weights
        if random.random() < 0.95:  # 95% chance to be during configured business hours
            # Generate time within business hours with weighting
            time_category = random.choices(
                ['morning', 'afternoon', 'evening'],
                weights=[
                    self.hour_weights['morning'],
                    self.hour_weights['afternoon'], 
                    self.hour_weights['evening']
                ],
                k=1
            )[0]
            
            # Map time category to hour range
            if time_category == 'morning':
                hour = random.randint(self.business_hours_start, 11)
            elif time_category == 'afternoon':
                hour = random.randint(12, self.business_hours_end - 1)
            else:  # evening
                hour = random.randint(self.business_hours_end, self.business_hours_end + 2)
        else:
            # 5% chance to be outside business hours
            if random.random() < 0.5:
                # Early morning (before business hours)
                hour = random.randint(self.business_hours_start - 3, self.business_hours_start - 1)
            else:
                # Late evening (after business hours)
                hour = random.randint(self.business_hours_end + 3, 23)
        
        # Generate random minute and second
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        # Create timestamp
        timestamp_dt = datetime(
            random_date.year, random_date.month, random_date.day,
            hour, minute, second
        )
        
        # Ensure timestamp is within our range
        if timestamp_dt < start_dt:
            timestamp_dt = start_dt
        elif timestamp_dt > end_dt:
            timestamp_dt = end_dt
            
        return timestamp_dt.isoformat()
    
    def generate_message_timestamps(self, 
                                  conversation_timestamp: str,
                                  num_messages: int) -> List[str]:
        """
        Generate timestamps for each message in a conversation with realistic delays.
        
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
        
        # Generate timestamps with realistic gaps between messages
        current_dt = start_dt
        for i in range(1, num_messages):
            # Add a random delay for response time and typing
            # More complex messages (longer ones) take more time to compose
            message_length_factor = 1.0  # Could be tied to message length if available
            
            # Use normal distribution for delay, but ensure it's positive
            delay_seconds = max(
                5,  # Minimum 5 second delay
                random.normalvariate(
                    self.message_delay_mean * message_length_factor,
                    self.message_delay_std_dev
                )
            )
            
            # Add occasional longer pause (e.g., person stepped away)
            if random.random() < 0.1:  # 10% chance
                delay_seconds += random.randint(60, 300)  # Add 1-5 minutes
                
            current_dt = current_dt + timedelta(seconds=delay_seconds)
            timestamps.append(current_dt)
        
        return [dt.isoformat() for dt in timestamps]
    
    def get_message_count_distribution(self, 
                                      time_period: Tuple[str, str], 
                                      total_conversations: int) -> Dict[str, int]:
        """
        Get distribution of conversations across a time period.
        
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
        
        # Create weightings for each day based on weekday/weekend
        day_weights = {}
        current_dt = start_dt
        
        # Calculate total weight for normalization
        total_weight = 0
        while current_dt <= end_dt:
            day_of_week = current_dt.weekday()
            is_weekend = day_of_week >= 5
            
            if is_weekend:
                # Share weekend weight between Saturday and Sunday
                weight = self.weekend_weight / 2
            else:
                # Use specific weekday weight
                day_name = current_dt.strftime('%A')
                weight = (1 - self.weekend_weight) * self.weekday_weights.get(day_name, 0.2)
                
            day_weights[current_dt.date().isoformat()] = weight
            total_weight += weight
            current_dt = current_dt + timedelta(days=1)
        
        # Normalize weights to ensure they sum to 1.0
        for day in day_weights:
            day_weights[day] /= total_weight
        
        # Distribute conversations based on weights
        remaining = total_conversations
        for day, weight in day_weights.items():
            count = int(total_conversations * weight)
            if remaining < count:
                count = remaining
            distribution[day] = count
            remaining -= count
        
        # Distribute any remaining conversations (due to rounding)
        while remaining > 0:
            # Add to highest weight days first
            sorted_days = sorted(day_weights.items(), key=lambda x: x[1], reverse=True)
            for day, _ in sorted_days:
                if remaining <= 0:
                    break
                distribution[day] += 1
                remaining -= 1
                
        return distribution