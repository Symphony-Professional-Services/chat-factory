"""
Base class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Different LLM services (Vertex AI, OpenAI, etc.) will have different APIs
    and implementation details. This class abstracts those differences.
    """
    
    def __init__(self, config):
        """
        Initialize the LLM provider with configuration.
        
        Args:
            config: Configuration object with necessary settings
        """
        self.config = config
    
    @abstractmethod
    async def initialize(self):
        """
        Initialize the LLM provider, setting up any necessary clients or sessions.
        """
        pass
    
    @abstractmethod
    async def generate_content(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Generate content using the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate (optional)
            
        Returns:
            Generated content as a string
        """
        pass
    
    @abstractmethod
    async def retry_with_backoff(self, prompt: str, max_retries: int = 10, 
                          initial_backoff: float = 1.0, max_backoff: float = 32.0) -> str:
        """
        Call the LLM with exponential backoff retry logic for handling rate limits.
        
        Args:
            prompt: The prompt to send to the LLM
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            
        Returns:
            Generated content as a string
        """
        pass