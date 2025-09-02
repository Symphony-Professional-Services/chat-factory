"""
Basic strategy for few-shot examples.
"""

import os
import logging
import glob
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

from ...strategies.base import FewShotExampleStrategy


class BasicFewShotStrategy(FewShotExampleStrategy):
    """
    Basic implementation of the few-shot example strategy.
    
    This strategy loads examples from file system based on conversation characteristics,
    with fallback options if specific examples aren't available.
    """
    
    def __init__(self, config):
        """
        Initialize the basic few-shot example strategy.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
    
    async def get_examples(self, conversation_type: str, category: str, topic: str, 
                   subtopic: str = None) -> List[str]:
        """
        Get few-shot examples based on conversation characteristics.
        
        This method attempts to find examples in the following order:
        1. Exact match for category/topic/subtopic
        2. Match for category/topic
        3. Match for just category
        4. Match for conversation_type
        5. Generic examples
        
        Args:
            conversation_type: Type of conversation
            category: Conversation category
            topic: Conversation topic
            subtopic: Conversation subtopic (optional)
            
        Returns:
            List of few-shot example strings
        """
        examples = []
        sanitized_category = self._sanitize_path_component(category)
        sanitized_topic = self._sanitize_path_component(topic)
        sanitized_conv_type = self._sanitize_path_component(conversation_type)
        
        # Try multiple paths in order of specificity
        example_paths = []
        
        # 1. Most specific: category/topic/subtopic
        if subtopic:
            sanitized_subtopic = self._sanitize_path_component(subtopic)
            example_paths.append(f"{sanitized_category}/{sanitized_topic}/{sanitized_subtopic}*.txt")
        
        # 2. Category and topic
        example_paths.append(f"{sanitized_category}/{sanitized_topic}*.txt")
        
        # 3. Just category
        example_paths.append(f"{sanitized_category}*.txt")
        
        # 4. Conversation type
        example_paths.append(f"{sanitized_conv_type}*.txt")
        
        # 5. Generic examples
        example_paths.append("generic*.txt")
        
        # Try each path pattern
        for path_pattern in example_paths:
            full_pattern = os.path.join(self.few_shot_examples_dir, path_pattern)
            matching_files = glob.glob(full_pattern)
            
            if matching_files:
                # Get up to 2 random examples from matching files
                selected_files = random.sample(matching_files, min(2, len(matching_files)))
                for file_path in selected_files:
                    example = await self.load_example_file(Path(file_path))
                    if example:
                        examples.append(example)
                
                # If we found at least one example, stop searching
                if examples:
                    break
        
        logging.info(f"Found {len(examples)} few-shot examples for {category}/{topic}/{subtopic or ''}")
        return examples
    
    def format_examples(self, examples: List[str]) -> str:
        """
        Format few-shot examples for inclusion in a prompt.
        
        Args:
            examples: List of few-shot examples
            
        Returns:
            Formatted string containing few-shot examples
        """
        if not examples:
            return ""
        
        formatted = "Here are some example conversations similar to what I want you to generate:\n\n"
        
        for i, example in enumerate(examples, 1):
            formatted += f"EXAMPLE {i}:\n{example}\n\n"
        
        formatted += "Now, generate a new conversation following a similar format, but don't copy these examples directly.\n"
        return formatted
    
    async def load_example_file(self, file_path: Path) -> str:
        """
        Load a few-shot example from a file.
        
        Args:
            file_path: Path to the example file
            
        Returns:
            Content of the example file
        """
        try:
            with open(file_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logging.error(f"Error loading few-shot example from {file_path}: {e}")
            return ""
    
    def _sanitize_path_component(self, component: str) -> str:
        """
        Sanitize a path component for use in file paths.
        
        Args:
            component: Path component to sanitize
            
        Returns:
            Sanitized path component
        """
        # Replace spaces, slashes, and other problematic characters
        sanitized = component.replace(' ', '_')
        sanitized = sanitized.replace('/', '_')
        sanitized = sanitized.replace('\\', '_')
        sanitized = sanitized.replace(':', '_')
        sanitized = sanitized.replace('*', '_')
        sanitized = sanitized.replace('?', '_')
        sanitized = sanitized.replace('"', '_')
        sanitized = sanitized.replace('<', '_')
        sanitized = sanitized.replace('>', '_')
        sanitized = sanitized.replace('|', '_')
        return sanitized.lower()