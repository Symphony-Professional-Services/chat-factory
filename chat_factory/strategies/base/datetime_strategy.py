"""
Base class for datetime distribution strategies.

This module defines the abstract base class for datetime distribution strategies
that control the temporal aspects of conversation generation.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from ...models.conversation import ChatLine


class DatetimeStrategy(ABC):
    """
    Abstract base class for datetime distribution strategies.
    
    Different use cases may need different distributions of conversations and messages
    over time periods like day, week, or month.
    """
    
    def __init__(self, config):
        """
        Initialize the datetime strategy with configuration.
        
        Args:
            config: Configuration object with necessary settings
        """
        self.config = config
    
    @abstractmethod
    def generate_conversation_timestamp(self, conversation_number: int) -> str:
        """
        Generate a timestamp for a conversation.
        
        Args:
            conversation_number: Sequence number for this conversation
            
        Returns:
            ISO format timestamp string
        """
        pass
        
    @abstractmethod
    def generate_message_timestamps(self, 
                                  conversation_timestamp: str,
                                  num_messages: int) -> List[str]:
        """
        Generate timestamps for each message in a conversation.
        
        Args:
            conversation_timestamp: Timestamp for the start of conversation
            num_messages: Number of messages to generate timestamps for
            
        Returns:
            List of ISO format timestamp strings
        """
        pass
    
    @abstractmethod
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
        pass
    
    def parse_date_range(self, start_date: str, end_date: str) -> Tuple[datetime, datetime]:
        """
        Parse ISO format date strings to datetime objects.
        
        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format
            
        Returns:
            Tuple of (start_datetime, end_datetime)
        """
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        return start_dt, end_dt
    
    def apply_timestamps_to_conversation(self, 
                                       chat_lines: List[ChatLine],
                                       timestamps: List[str]) -> List[ChatLine]:
        """
        Apply timestamps to a list of chat lines.
        
        Args:
            chat_lines: List of ChatLine objects
            timestamps: List of timestamp strings
            
        Returns:
            List of ChatLine objects with timestamps applied
        """
        if len(chat_lines) != len(timestamps):
            raise ValueError(f"Length mismatch: {len(chat_lines)} chat lines but {len(timestamps)} timestamps")
        
        # Create copies of chat lines with timestamps
        updated_lines = []
        for i, line in enumerate(chat_lines):
            updated_line = ChatLine(
                speaker=line.speaker,
                text=line.text,
                timestamp=timestamps[i]
            )
            updated_lines.append(updated_line)
        
        return updated_lines