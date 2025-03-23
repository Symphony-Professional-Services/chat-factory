"""
Base class for few-shot example strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class FewShotExampleStrategy(ABC):
    """
    Abstract base class for fetching and formatting few-shot examples.
    
    Different use cases may need different few-shot examples based on various criteria,
    and might format them differently for inclusion in prompts.
    """
    
    def __init__(self, config):
        """
        Initialize the few-shot example strategy with configuration.
        
        Args:
            config: Configuration object with necessary settings
        """
        self.config = config
        self.few_shot_examples_dir = Path(getattr(config, 'FEW_SHOT_EXAMPLES_DIR', 'few_shot_examples'))
    
    @abstractmethod
    async def get_examples(self, conversation_type: str, category: str, topic: str, 
                   subtopic: str = None) -> List[str]:
        """
        Get few-shot examples based on conversation characteristics.
        
        Args:
            conversation_type: Type of conversation
            category: Conversation category
            topic: Conversation topic
            subtopic: Conversation subtopic (optional)
            
        Returns:
            List of few-shot example strings
        """
        pass
    
    @abstractmethod
    def format_examples(self, examples: List[str]) -> str:
        """
        Format few-shot examples for inclusion in a prompt.
        
        Args:
            examples: List of few-shot examples
            
        Returns:
            Formatted string containing few-shot examples
        """
        pass
    
    @abstractmethod
    async def load_example_file(self, file_path: Path) -> str:
        """
        Load a few-shot example from a file.
        
        Args:
            file_path: Path to the example file
            
        Returns:
            Content of the example file
        """
        pass