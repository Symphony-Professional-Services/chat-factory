"""
Custom period datetime distribution strategy.

This strategy generates timestamps with fine-grained control over time periods.
"""

import random
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from ..base.datetime_strategy import DatetimeStrategy


class CustomPeriodStrategy(DatetimeStrategy):
    """
    Datetime strategy that provides fine-grained control over time distributions.
    
    This strategy allows for custom time distributions including:
    - Specific date ranges
    - Custom distributions within day/week/month
    - Season/holiday weighting
    - Custom message timing patterns
    """
    
    def __init__(self, config):
        """
        Initialize the custom period datetime strategy.
        
        Args:
            config: Configuration with settings for time distribution
        """
        super().__init__(config)
        
        # Default settings if not specified in config
        self.start_date = getattr(config, 'START_DATE', datetime.now().isoformat())
        self.end_date = getattr(config, 'END_DATE', 
                               (datetime.now() + timedelta(days=30)).isoformat())
        
        # Hour-based weights (0-23)
        self.hour_weights = getattr(config, 'HOUR_WEIGHTS', {})
        if not self.hour_weights:
            # Default to business hours weight if not specified
            self.hour_weights = {h: 0.0 for h in range(24)}
            # Business hours get higher weights
            for h in range(9, 18):
                self.hour_weights[h] = 1.0
            # Early morning and evening get medium weights
            for h in range(7, 9):
                self.hour_weights[h] = 0.5
            for h in range(18, 21):
                self.hour_weights[h] = 0.5
                
        # Day of week weights (0=Monday, 6=Sunday)
        self.day_weights = getattr(config, 'DAY_WEIGHTS', {})
        if not self.day_weights:
            # Default to weekday weighting if not specified
            self.day_weights = {
                0: 1.0,  # Monday
                1: 1.0,  # Tuesday
                2: 1.0,  # Wednesday
                3: 1.0,  # Thursday
                4: 1.0,  # Friday
                5: 0.3,  # Saturday
                6: 0.2   # Sunday
            }
            
        # Month weights (1-12)
        self.month_weights = getattr(config, 'MONTH_WEIGHTS', {})
        if not self.month_weights:
            # Default to equal weighting for all months
            self.month_weights = {m: 1.0 for m in range(1, 13)}
        
        # Special date weights - allows for holiday emphasis
        self.special_dates = getattr(config, 'SPECIAL_DATES', {})
        # Example format: {'2025-01-01': 0.2, '2025-12-25': 0.1}
        
        # Message timing patterns
        self.message_timing_patterns = getattr(config, 'MESSAGE_TIMING_PATTERNS', {})
        if not self.message_timing_patterns:
            # Default patterns
            self.message_timing_patterns = {
                'quick_exchange': {
                    'mean_delay': 20,     # 20 seconds between messages
                    'std_dev': 10,         # 10 seconds standard deviation
                    'probability': 0.3     # 30% chance of this pattern
                },
                'normal_conversation': {
                    'mean_delay': 60,     # 1 minute between messages
                    'std_dev': 30,         # 30 seconds standard deviation
                    'probability': 0.5     # 50% chance of this pattern
                },
                'thoughtful_discussion': {
                    'mean_delay': 180,    # 3 minutes between messages
                    'std_dev': 60,         # 1 minute standard deviation
                    'probability': 0.2     # 20% chance of this pattern
                }
            }
        
        logging.info(f"Custom period strategy initialized with date range: {self.start_date} to {self.end_date}")
    
    def generate_conversation_timestamp(self, conversation_number: int) -> str:
        """
        Generate a timestamp based on custom period configuration.
        
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
            else:
                # Fall back to random date within range, but log a warning
                logging.warning(f"Conversation number {conversation_number} exceeds pre-calculated distribution size " +
                               f"({len(self._distribution_dates)}). Using random date within range.")
                base_date = start_dt + timedelta(
                    seconds=random.randint(0, int((end_dt - start_dt).total_seconds()))
                )
        else:
            # No distribution calculated yet, use weighted random selection within range
            base_date = self._select_weighted_date(start_dt, end_dt)
        
        # Select hour based on weights
        hour_options = list(range(24))
        hour_weights = [self.hour_weights.get(h, 0.1) for h in hour_options]
        
        # Normalize weights
        total_weight = sum(hour_weights)
        if total_weight == 0:
            hour_weights = [1.0] * 24  # Equal weights if all zeros
        else:
            hour_weights = [w / total_weight for w in hour_weights]
            
        hour = random.choices(hour_options, weights=hour_weights, k=1)[0]
        
        # Random minute and second
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        # Combine date and time
        timestamp_dt = datetime(
            base_date.year, base_date.month, base_date.day, 
            hour, minute, second
        )
        
        # Ensure timestamp is within range
        if timestamp_dt < start_dt:
            timestamp_dt = start_dt
        elif timestamp_dt > end_dt:
            timestamp_dt = end_dt
            
        return timestamp_dt.isoformat()
    
    def _select_weighted_date(self, start_dt: datetime, end_dt: datetime) -> datetime:
        """
        Select a date using the configured weights.
        
        Args:
            start_dt: Start of date range
            end_dt: End of date range
            
        Returns:
            Selected datetime
        """
        # Check for special dates first
        if self.special_dates and random.random() < 0.2:  # 20% chance to use special date
            special_dates = []
            special_weights = []
            
            for date_str, weight in self.special_dates.items():
                try:
                    date_dt = datetime.fromisoformat(date_str + 'T00:00:00')
                    if start_dt <= date_dt <= end_dt:
                        special_dates.append(date_dt)
                        special_weights.append(weight)
                except ValueError:
                    logging.warning(f"Invalid date format in special_dates: {date_str}")
            
            if special_dates:
                # Normalize weights
                total_weight = sum(special_weights)
                normalized_weights = [w / total_weight for w in special_weights]
                return random.choices(special_dates, weights=normalized_weights, k=1)[0]
        
        # Random date selection with weighting
        current_dt = start_dt
        candidate_dates = []
        date_weights = []
        
        while current_dt <= end_dt:
            # Get day of week weight (0=Monday, 6=Sunday)
            day_of_week = current_dt.weekday()
            day_weight = self.day_weights.get(day_of_week, 0.1)
            
            # Get month weight
            month_weight = self.month_weights.get(current_dt.month, 1.0)
            
            # Combine weights
            combined_weight = day_weight * month_weight
            
            candidate_dates.append(current_dt)
            date_weights.append(combined_weight)
            
            current_dt = current_dt + timedelta(days=1)
        
        # Normalize weights
        total_weight = sum(date_weights)
        if total_weight == 0:
            date_weights = [1.0] * len(candidate_dates)  # Equal weights if all zeros
        else:
            date_weights = [w / total_weight for w in date_weights]
        
        # Select weighted random date
        selected_date = random.choices(candidate_dates, weights=date_weights, k=1)[0]
        return selected_date
    
    def generate_message_timestamps(self, 
                                  conversation_timestamp: str,
                                  num_messages: int) -> List[str]:
        """
        Generate timestamps for each message with custom timing patterns.
        
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
        
        # Select a message timing pattern
        patterns = list(self.message_timing_patterns.keys())
        weights = [self.message_timing_patterns[p]['probability'] for p in patterns]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1.0] * len(patterns)  # Equal weights if all zeros
        else:
            weights = [w / total_weight for w in weights]
            
        selected_pattern = random.choices(patterns, weights=weights, k=1)[0]
        pattern = self.message_timing_patterns[selected_pattern]
        
        # Generate timestamps using selected pattern
        current_dt = start_dt
        for i in range(1, num_messages):
            # Get delay parameters from pattern
            mean_delay = pattern['mean_delay']
            std_dev = pattern['std_dev']
            
            # Calculate delay with variation based on message position
            # Messages tend to slow down as conversation progresses
            position_factor = 1.0 + (i / num_messages) * 0.5  # Increases delay up to 50% by end
            
            delay_seconds = max(
                5,  # Minimum 5 second delay
                random.normalvariate(
                    mean_delay * position_factor,
                    std_dev
                )
            )
            
            # Add occasional longer pause
            if random.random() < 0.05:  # 5% chance
                pause_duration = random.choice([
                    random.randint(180, 300),    # 3-5 minutes
                    random.randint(600, 1200),   # 10-20 minutes
                    random.randint(3600, 7200)   # 1-2 hours (e.g., meal break)
                ])
                delay_seconds += pause_duration
                
            current_dt = current_dt + timedelta(seconds=delay_seconds)
            timestamps.append(current_dt)
        
        return [dt.isoformat() for dt in timestamps]
    
    def get_message_count_distribution(self, 
                                      time_period: Tuple[str, str], 
                                      total_conversations: int) -> Dict[str, int]:
        """
        Get custom distribution of conversations across a time period.
        
        Args:
            time_period: Tuple of (start_date, end_date) as ISO format strings
            total_conversations: Total number of conversations to distribute
            
        Returns:
            Dictionary mapping dates to conversation counts
        """
        start_dt, end_dt = self.parse_date_range(time_period[0], time_period[1])
        
        # Initialize distribution with zeros for all dates
        distribution = {}
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.date().isoformat()
            distribution[date_str] = 0
            current_dt = current_dt + timedelta(days=1)
        
        # Calculate weights for each date
        date_weights = {}
        current_dt = start_dt
        total_weight = 0
        
        while current_dt <= end_dt:
            date_str = current_dt.date().isoformat()
            
            # Check if it's a special date
            special_weight = self.special_dates.get(date_str, 1.0)
            
            # Get day of week weight
            day_of_week = current_dt.weekday()
            day_weight = self.day_weights.get(day_of_week, 0.1)
            
            # Get month weight
            month_weight = self.month_weights.get(current_dt.month, 1.0)
            
            # Combine weights
            combined_weight = special_weight * day_weight * month_weight
            date_weights[date_str] = combined_weight
            total_weight += combined_weight
            
            current_dt = current_dt + timedelta(days=1)
        
        # Normalize weights
        if total_weight == 0:
            # Equal distribution if all weights are zero
            days = len(distribution)
            base = total_conversations // days
            extra = total_conversations % days
            
            for date_str in distribution:
                distribution[date_str] = base
                
            # Distribute remainder
            dates = list(distribution.keys())
            for i in range(extra):
                distribution[dates[i]] += 1
        else:
            # Weighted distribution
            remaining = total_conversations
            
            # First pass - integer distribution
            for date_str, weight in date_weights.items():
                normalized_weight = weight / total_weight
                count = int(total_conversations * normalized_weight)
                distribution[date_str] = count
                remaining -= count
                
            # Second pass - distribute remaining
            if remaining > 0:
                # Sort dates by weight descending
                sorted_dates = sorted(date_weights.items(), key=lambda x: x[1], reverse=True)
                for date_str, _ in sorted_dates:
                    if remaining <= 0:
                        break
                    distribution[date_str] += 1
                    remaining -= 1
        
        # Store distribution dates for conversation timestamp generation
        self._distribution_dates = []
        for date_str, count in distribution.items():
            self._distribution_dates.extend([date_str] * count)
            
        # Shuffle to avoid sequential ordering
        random.shuffle(self._distribution_dates)
        
        return distribution