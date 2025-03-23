"""
Base class for taxonomy processing strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from ...models.taxonomy import Taxonomy, TaxonomyTopic


class TaxonomyStrategy(ABC):
    """
    Abstract base class for taxonomy processing strategies.
    
    Different use cases may have different taxonomy structures and selection logic.
    This strategy abstracts those differences.
    """
    
    def __init__(self, config):
        """
        Initialize the taxonomy strategy with configuration.
        
        Args:
            config: Configuration object with necessary settings
        """
        self.config = config
        self.taxonomy = None
    
    @abstractmethod
    def load_taxonomy(self, taxonomy_file: str) -> Taxonomy:
        """
        Load and parse taxonomy from file.
        
        Args:
            taxonomy_file: Path to the taxonomy file
            
        Returns:
            Parsed Taxonomy object
        """
        pass
        
    @abstractmethod
    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        Flatten taxonomy into a consistent format.
        
        Args:
            taxonomy: Raw taxonomy data
            
        Returns:
            List of tuples in the format (category, topic, subtopic)
        """
        pass
        
    @abstractmethod
    def select_topic(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
        """
        Select a topic from the flattened taxonomy.
        
        Args:
            flattened_taxonomy: List of flattened taxonomy tuples
            
        Returns:
            Selected topic as (category, topic, subtopic)
        """
        pass
    
    @abstractmethod
    def detect_taxonomy_format(self, taxonomy: Dict[str, Any]) -> str:
        """
        Detect the format of the taxonomy.
        
        Args:
            taxonomy: Raw taxonomy data
            
        Returns:
            String identifier for the taxonomy format
        """
        pass