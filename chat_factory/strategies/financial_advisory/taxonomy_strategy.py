"""
Taxonomy strategy for financial advisory use case.
"""

import json
import logging
import random
from typing import List, Dict, Any, Tuple
from pathlib import Path
#import aiofiles

from ...models.taxonomy import Taxonomy, TaxonomyTopic
from ..base import TaxonomyStrategy


class FinancialAdvisoryTaxonomyStrategy(TaxonomyStrategy):
    """
    Implementation of taxonomy strategy for financial advisory conversations.
    
    This strategy handles the hierarchical financial advisory taxonomy format, which
    includes categories, topics, and subtopics.
    """
    
    def __init__(self, config):
        """
        Initialize the financial advisory taxonomy strategy.
        
        Args:
            config: Configuration with taxonomy settings
        """
        super().__init__(config)
        self.topic_distribution = getattr(config, 'TOPIC_DISTRIBUTION', 'uniform')
    
    def load_taxonomy(self, taxonomy_file: str) -> Taxonomy:
        """
        Load and parse financial advisory taxonomy from file.
        
        Args:
            taxonomy_file: Path to the taxonomy file
            
        Returns:
            Parsed Taxonomy object
        """
        logging.info(f"Loading financial advisory taxonomy from: {taxonomy_file}")
        
        try:
            with open(taxonomy_file, 'r') as f:
                raw_taxonomy = json.load(f)
            
            # Validate the taxonomy structure
            if not raw_taxonomy:
                logging.error(f"Empty taxonomy loaded from {taxonomy_file}")
                return Taxonomy(name="empty")
            
            taxonomy = Taxonomy(
                name="financial_advisory",
                raw_data=raw_taxonomy
            )
            
            # Process the raw taxonomy into structured topics
            taxonomy.topics = self._extract_topics(raw_taxonomy)
            
            logging.info(f"Successfully loaded financial advisory taxonomy with {len(taxonomy.topics)} topics")
            return taxonomy
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error loading taxonomy file {taxonomy_file}: {e}")
            return Taxonomy(name="error")
    

    # async def load_taxonomy_async(self, taxonomy_file: str) -> Taxonomy:
    #     logging.info(f"Loading financial advisory taxonomy asynchronously from: {taxonomy_file}")
    #     try:
    #         async with aiofiles.open(taxonomy_file, mode='r') as f:
    #             content = await f.read()
    #         raw_taxonomy = json.loads(content) # Use loads with the string content

    #         # Validate the taxonomy structure
    #         if not raw_taxonomy:
    #             logging.error(f"Empty taxonomy loaded from {taxonomy_file}")
    #             return Taxonomy(name="empty")
            
    #         taxonomy = Taxonomy(
    #             name="financial_advisory",
    #             raw_data=raw_taxonomy
    #         )

    #         taxonomy.topics = self._extract_topics(raw_taxonomy) # This remains sync
            
    #         logging.info(f"Successfully loaded financial advisory taxonomy with {len(taxonomy.topics)} topics")
    #         return taxonomy
        
    #     except (json.JSONDecodeError, FileNotFoundError) as e:
    #         logging.error(f"Error loading taxonomy file {taxonomy_file}: {e}")
    #         return Taxonomy(name="error")
        
    #     except Exception as e: # Catch other potential errors
    #         logging.error(f"Unexpected error loading taxonomy {taxonomy_file}: {e}", exc_info=True)
    #         return Taxonomy(name="error")

    def _extract_topics(self, raw_taxonomy: Dict[str, Any]) -> List[TaxonomyTopic]:
        """
        Extract structured topics from raw taxonomy data.
        
        Args:
            raw_taxonomy: Raw taxonomy dictionary
            
        Returns:
            List of TaxonomyTopic objects
        """
        topics = []
        
        for category, items in raw_taxonomy.items():
            if isinstance(items, dict):
                # Category contains subcategories/topics
                for topic, subtopics in items.items():
                    if isinstance(subtopics, list):
                        # Add each subtopic with full hierarchy
                        for subtopic in subtopics:
                            topics.append(TaxonomyTopic(
                                category=category,
                                topic=topic,
                                subtopic=subtopic
                            ))
                    else:
                        # Handle case where a topic has no subtopics
                        topics.append(TaxonomyTopic(
                            category=category,
                            topic=topic
                        ))
            elif isinstance(items, list):
                # Category contains direct topics without subcategories
                for topic in items:
                    topics.append(TaxonomyTopic(
                        category=category,
                        topic=topic
                    ))
        
        return topics
    
    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        Flatten taxonomy into a consistent format.
        
        Args:
            taxonomy: Raw taxonomy data
            
        Returns:
            List of tuples in the format (category, topic, subtopic)
        """
        flattened = []
        
        for category, items in taxonomy.items():
            if isinstance(items, dict):
                # Category contains subcategories/topics
                for topic, subtopics in items.items():
                    if isinstance(subtopics, list):
                        # Add each subtopic with full hierarchy
                        for subtopic in subtopics:
                            flattened.append((category, topic, subtopic))
                    else:
                        # Handle case where a topic has no subtopics
                        flattened.append((category, topic, ""))
            elif isinstance(items, list):
                # Category contains direct topics without subcategories
                for topic in items:
                    flattened.append((category, topic, ""))
        
        logging.info(f"Flattened financial advisory taxonomy into {len(flattened)} unique topic paths")
        return flattened
    
    def select_topic(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
        """
        Select a topic from the flattened taxonomy.
        
        Args:
            flattened_taxonomy: List of flattened taxonomy tuples
            
        Returns:
            Selected topic as (category, topic, subtopic)
        """
        if not flattened_taxonomy:
            logging.warning("No flattened topics available. Using default topic.")
            return ("General", "General Conversation", "")
        
        # For now, simple uniform distribution
        # TODO: Implement weighted distributions based on topic_distribution setting
        category, topic, subtopic = random.choice(flattened_taxonomy)
        
        logging.info(f"Selected topic: category='{category}', topic='{topic}', subtopic='{subtopic}'")
        return (category, topic, subtopic)
    
    def detect_taxonomy_format(self, taxonomy: Dict[str, Any]) -> str:
        """
        Detect the format of the taxonomy.
        
        Args:
            taxonomy: Raw taxonomy data
            
        Returns:
            String identifier for the taxonomy format
        """
        if "conversation_types" in taxonomy:
            return "company_tagging"
        else:
            return "financial_advisory"