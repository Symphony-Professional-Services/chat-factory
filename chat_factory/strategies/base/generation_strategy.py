"""
Base class for conversation generation strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional


class GenerationStrategy(ABC):
    """
    Abstract base class for conversation generation strategies.
    
    Different use cases may have different requirements for prompt construction,
    manifest blueprints, and response processing.
    """
    
    def __init__(self, config):
        """
        Initialize the generation strategy with configuration.
        
        Args:
            config: Configuration object with necessary settings
        """
        self.config = config
    
    @abstractmethod
    def create_manifest_blueprint(self, conversation_type: str, topic: Tuple[str, str, str], 
                                  num_messages: int) -> Dict[str, Any]:
        """
        Create a manifest blueprint for a conversation.
        
        Args:
            conversation_type: Type of conversation to generate
            topic: Selected topic as (category, topic, subtopic)
            num_messages: Number of messages to generate
            
        Returns:
            Dictionary containing blueprint for conversation generation
        """
        pass
        
    @abstractmethod
    async def construct_prompt(self, advisor_name: str, client_name: str, 
                        conversation_type: str, num_messages: int, 
                        manifest_blueprint: Dict[str, Any],
                        few_shot_examples: List[str]) -> str:
        """
        Construct a prompt for conversation generation.
        
        Args:
            advisor_name: Name of the advisor
            client_name: Name of the client
            conversation_type: Type of conversation
            num_messages: Number of messages to generate
            manifest_blueprint: Blueprint for the conversation
            few_shot_examples: List of few-shot examples to include in the prompt
            
        Returns:
            Complete prompt string for LLM
        """
        pass
        
    @abstractmethod
    def process_llm_response(self, llm_response: str) -> List[Dict[str, str]]:
        """
        Process LLM response into standardized conversation format.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            List of dictionaries representing chat lines
        """
        pass