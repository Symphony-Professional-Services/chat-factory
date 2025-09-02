"""
Tests for datetime distribution strategies.
"""

import unittest
from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
import json
from unittest.mock import patch, MagicMock

from chat_factory.strategies.base.datetime_strategy import DatetimeStrategy
from chat_factory.strategies.datetime_distribution.business_hours_strategy import BusinessHoursDatetimeStrategy
from chat_factory.strategies.datetime_distribution.uniform_distribution_strategy import UniformDistributionStrategy
from chat_factory.strategies.datetime_distribution.custom_period_strategy import CustomPeriodStrategy
from chat_factory.models.conversation import ChatLine


class TestDatetimeStrategy(unittest.TestCase):
    """Test cases for datetime strategies."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock config with datetime settings
        self.config = MagicMock()
        self.config.START_DATE = '2025-01-01T00:00:00'
        self.config.END_DATE = '2025-03-31T23:59:59'
        self.config.BUSINESS_HOURS_START = 9  # 9 AM
        self.config.BUSINESS_HOURS_END = 17   # 5 PM
        self.config.WEEKEND_WEIGHT = 0.2      # 20% of conversations on weekends
        self.config.WEEKDAY_WEIGHTS = {
            'Monday': 0.25,
            'Tuesday': 0.2,
            'Wednesday': 0.2,
            'Thursday': 0.2,
            'Friday': 0.15
        }
        self.config.HOUR_WEIGHTS = {
            'morning': 0.3,     # 9am-12pm
            'afternoon': 0.5,   # 12pm-5pm
            'evening': 0.2      # 5pm-8pm
        }
        self.config.MESSAGE_DELAY_MEAN = 60    # Mean delay between messages in seconds
        self.config.MESSAGE_DELAY_STD_DEV = 30  # Standard deviation for delay
        
        # Initialize strategies with mock config
        self.business_hours_strategy = BusinessHoursDatetimeStrategy(self.config)
        self.uniform_strategy = UniformDistributionStrategy(self.config)
        self.custom_strategy = CustomPeriodStrategy(self.config)

    def test_parse_date_range(self):
        """Test parsing date range works correctly."""
        start_dt, end_dt = self.business_hours_strategy.parse_date_range(
            self.config.START_DATE, 
            self.config.END_DATE
        )
        
        self.assertEqual(start_dt, datetime.fromisoformat('2025-01-01T00:00:00'))
        self.assertEqual(end_dt, datetime.fromisoformat('2025-03-31T23:59:59'))

    def test_generate_conversation_timestamp_in_range(self):
        """Test conversation timestamp is within configured date range."""
        # Test with multiple timestamps
        timestamps = []
        for i in range(100):  # Generate 100 timestamps for statistical testing
            timestamp = self.business_hours_strategy.generate_conversation_timestamp(i)
            dt = datetime.fromisoformat(timestamp)
            timestamps.append(dt)
            
            # Check timestamp is within range
            self.assertGreaterEqual(dt, datetime.fromisoformat(self.config.START_DATE))
            self.assertLessEqual(dt, datetime.fromisoformat(self.config.END_DATE))
            
        # Check that timestamps are actually distributed across the range
        # Get min and max dates
        min_date = min(timestamps).date()
        max_date = max(timestamps).date()
        
        # Calculate date range in days
        start_date = datetime.fromisoformat(self.config.START_DATE).date()
        end_date = datetime.fromisoformat(self.config.END_DATE).date()
        expected_range_days = (end_date - start_date).days
        
        # Check that we're using a reasonable portion of the range
        # We may not hit the exact endpoints due to randomness, but should use at least 50% of the range
        actual_range_days = (max_date - min_date).days
        coverage_ratio = actual_range_days / expected_range_days if expected_range_days > 0 else 0
        
        self.assertGreaterEqual(coverage_ratio, 0.5, 
            f"Generated timestamps only cover {actual_range_days} days out of {expected_range_days} days range")

    def test_generate_message_timestamps(self):
        """Test generating timestamps for messages within a conversation."""
        conversation_timestamp = "2025-02-15T14:30:00"
        num_messages = 5
        
        message_timestamps = self.business_hours_strategy.generate_message_timestamps(
            conversation_timestamp, num_messages
        )
        
        # Check we got the right number of timestamps
        self.assertEqual(len(message_timestamps), num_messages)
        
        # Convert timestamps to datetime objects for comparison
        dt_timestamps = [datetime.fromisoformat(ts) for ts in message_timestamps]
        
        # Check timestamps are in ascending order
        self.assertEqual(dt_timestamps, sorted(dt_timestamps))
        
        # Check first timestamp matches conversation timestamp
        self.assertEqual(dt_timestamps[0], datetime.fromisoformat(conversation_timestamp))
        
        # Check delays between messages are reasonable
        for i in range(1, len(dt_timestamps)):
            delay = (dt_timestamps[i] - dt_timestamps[i-1]).total_seconds()
            # Delay should be positive and within reasonable bounds (1-300 seconds)
            self.assertGreater(delay, 0)
            self.assertLess(delay, 300)

    def test_get_message_count_distribution(self):
        """Test message count distribution for a time period."""
        period_start = "2025-01-01T00:00:00"
        period_end = "2025-01-31T23:59:59"  # January 2025 (31 days)
        num_conversations = 100
        
        # Get the distribution
        distribution = self.business_hours_strategy.get_message_count_distribution(
            (period_start, period_end), num_conversations
        )
        
        # Check distribution contains all days in the period
        start_dt = datetime.fromisoformat(period_start)
        end_dt = datetime.fromisoformat(period_end)
        days_in_period = (end_dt.date() - start_dt.date()).days + 1
        
        self.assertEqual(len(distribution), days_in_period)
        
        # Check total conversations matches requested
        total = sum(distribution.values())
        self.assertEqual(total, num_conversations)
        
        # Check weekday distribution follows weights - can only check approximately
        weekday_counts = {day: 0 for day in range(7)}  # 0=Monday, 6=Sunday
        
        for date_str, count in distribution.items():
            date_dt = datetime.fromisoformat(date_str + "T00:00:00")
            weekday = date_dt.weekday()
            weekday_counts[weekday] += count
            
        # Weekend days should have fewer conversations than weekdays on average
        avg_weekday = sum(weekday_counts[i] for i in range(5)) / 5
        avg_weekend = sum(weekday_counts[i] for i in range(5, 7)) / 2
        
        self.assertGreater(avg_weekday, avg_weekend)
        
    def test_strict_distribution_integrity(self):
        """Test that distribution strictly adheres to the time period."""
        # Very short time period (3 days)
        period_start = "2025-01-01T00:00:00"
        period_end = "2025-01-03T23:59:59"  # Just 3 days
        num_conversations = 50
        
        # Test with each strategy
        for strategy in [self.business_hours_strategy, self.uniform_strategy, self.custom_strategy]:
            # Override configuration to use the short period
            strategy.start_date = period_start
            strategy.end_date = period_end
            
            # Get the distribution
            distribution = strategy.get_message_count_distribution(
                (period_start, period_end), num_conversations
            )
            
            # Verify days in distribution
            self.assertEqual(len(distribution), 3, f"Expected exactly 3 days in distribution, got {len(distribution)}")
            
            # Verify all dates are within range
            for date_str in distribution.keys():
                date_dt = datetime.fromisoformat(date_str + "T00:00:00").date()
                start_date = datetime.fromisoformat(period_start).date()
                end_date = datetime.fromisoformat(period_end).date()
                
                self.assertGreaterEqual(date_dt, start_date)
                self.assertLessEqual(date_dt, end_date)
                
            # Verify sum equals requested conversations
            self.assertEqual(sum(distribution.values()), num_conversations)
            
            # Generate actual timestamps based on this distribution
            # This is to verify that the generated timestamps match the distribution
            # Rebuild internal distribution dates list (reset any existing state)
            strategy._distribution_dates = []
            for date_str, count in distribution.items():
                strategy._distribution_dates.extend([date_str] * count)
            random.shuffle(strategy._distribution_dates)
            
            # Generate timestamps for all conversations
            generated_timestamps = []
            for i in range(num_conversations):
                timestamp = strategy.generate_conversation_timestamp(i)
                generated_timestamps.append(timestamp)
            
            # Verify all timestamps are within range
            for ts in generated_timestamps:
                dt = datetime.fromisoformat(ts)
                self.assertGreaterEqual(dt, datetime.fromisoformat(period_start))
                self.assertLessEqual(dt, datetime.fromisoformat(period_end))
                
            # Count timestamps by date
            date_counts = {}
            for ts in generated_timestamps:
                date_str = datetime.fromisoformat(ts).date().isoformat()
                if date_str not in date_counts:
                    date_counts[date_str] = 0
                date_counts[date_str] += 1
                
            # Verify counts match distribution
            for date_str, count in distribution.items():
                self.assertEqual(date_counts.get(date_str, 0), count, 
                               f"Expected {count} timestamps on {date_str}, got {date_counts.get(date_str, 0)}")

    def test_apply_timestamps_to_conversation(self):
        """Test applying timestamps to a conversation's chat lines."""
        # Create a mock conversation with 3 messages
        conversation_timestamp = "2025-02-15T14:30:00"
        chat_lines = [
            ChatLine(speaker="0", text="Hello"),
            ChatLine(speaker="1", text="Hi there"),
            ChatLine(speaker="0", text="How are you?")
        ]
        
        # Generate timestamps and apply them
        message_timestamps = self.business_hours_strategy.generate_message_timestamps(
            conversation_timestamp, len(chat_lines)
        )
        
        updated_lines = self.business_hours_strategy.apply_timestamps_to_conversation(
            chat_lines, message_timestamps
        )
        
        # Check all lines have timestamps
        for i, line in enumerate(updated_lines):
            self.assertEqual(line.timestamp, message_timestamps[i])
            
        # Check other properties are preserved
        for i, line in enumerate(updated_lines):
            self.assertEqual(line.speaker, chat_lines[i].speaker)
            self.assertEqual(line.text, chat_lines[i].text)

    def test_uniform_distribution_strategy(self):
        """Test the uniform distribution strategy generates valid timestamps."""
        # Generate some timestamps
        timestamps = []
        for i in range(20):
            timestamp = self.uniform_strategy.generate_conversation_timestamp(i)
            timestamps.append(timestamp)
            
        # Verify all timestamps are within range
        start_dt = datetime.fromisoformat(self.config.START_DATE)
        end_dt = datetime.fromisoformat(self.config.END_DATE)
        
        for ts in timestamps:
            dt = datetime.fromisoformat(ts)
            self.assertGreaterEqual(dt, start_dt)
            self.assertLessEqual(dt, end_dt)
            
    def test_short_time_period_strict_adherence(self):
        """Test strict adherence to short time periods (few days)."""
        # Configure a very short time period (3 days)
        short_config = MagicMock()
        short_config.START_DATE = '2025-01-01T00:00:00'
        short_config.END_DATE = '2025-01-03T23:59:59'  # Just 3 days
        
        # Create strategies with the short time period
        business_hours = BusinessHoursDatetimeStrategy(short_config)
        uniform = UniformDistributionStrategy(short_config)
        custom = CustomPeriodStrategy(short_config)
        
        # Test each strategy
        for strategy in [business_hours, uniform, custom]:
            # Generate 50 timestamps
            timestamps = []
            for i in range(50):
                timestamp = strategy.generate_conversation_timestamp(i)
                dt = datetime.fromisoformat(timestamp)
                timestamps.append(dt)
                
                # Strictly verify each timestamp is within the 3-day range
                self.assertGreaterEqual(dt, datetime.fromisoformat(short_config.START_DATE))
                self.assertLessEqual(dt, datetime.fromisoformat(short_config.END_DATE))
            
            # Verify we have at least one timestamp on each of the three days
            days = {dt.date() for dt in timestamps}
            expected_days = {
                datetime.fromisoformat('2025-01-01T00:00:00').date(),
                datetime.fromisoformat('2025-01-02T00:00:00').date(),
                datetime.fromisoformat('2025-01-03T00:00:00').date()
            }
            
            # Check that we have timestamps on each expected day
            self.assertTrue(
                days.issuperset(expected_days) or days == expected_days, 
                f"Missing days in distribution. Expected all of {expected_days}, got {days}"
            )

    def test_custom_period_strategy(self):
        """Test the custom period strategy."""
        # Set up some special dates
        self.custom_strategy.special_dates = {
            '2025-01-01': 2.0,  # New Year's Day
            '2025-01-15': 1.5   # Mid-month
        }
        
        # Generate timestamps
        timestamps = []
        for i in range(50):
            ts = self.custom_strategy.generate_conversation_timestamp(i)
            timestamps.append(ts)
            
        # Verify all are in range
        start_dt = datetime.fromisoformat(self.config.START_DATE)
        end_dt = datetime.fromisoformat(self.config.END_DATE)
        
        for ts in timestamps:
            dt = datetime.fromisoformat(ts)
            self.assertGreaterEqual(dt, start_dt)
            self.assertLessEqual(dt, end_dt)
            
        # Test distribution over extended period
        period_start = "2025-01-01T00:00:00"
        period_end = "2025-03-31T23:59:59"  # Q1 2025
        num_conversations = 200
        
        distribution = self.custom_strategy.get_message_count_distribution(
            (period_start, period_end), num_conversations
        )
        
        # Verify total matches requested
        self.assertEqual(sum(distribution.values()), num_conversations)


if __name__ == '__main__':
    unittest.main()