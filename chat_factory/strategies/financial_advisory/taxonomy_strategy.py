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
    
    # def select_topic(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
    #     """
    #     Select a topic from the flattened taxonomy.
        
    #     Args:
    #         flattened_taxonomy: List of flattened taxonomy tuples
            
    #     Returns:
    #         Selected topic as (category, topic, subtopic)
    #     """
    #     if not flattened_taxonomy:
    #         logging.warning("No flattened topics available. Using default topic.")
    #         return ("General", "General Conversation", "")
        
    #     # For now, simple uniform distribution
    #     # TODO: Implement weighted distributions based on topic_distribution setting
    #     category, topic, subtopic = random.choice(flattened_taxonomy)
        
    #     logging.info(f"Selected topic: category='{category}', topic='{topic}', subtopic='{subtopic}'")
    #     return (category, topic, subtopic)


    def select_topic(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
        """
        Select a topic from the flattened taxonomy based on the configured distribution.

        Args:
            flattened_taxonomy: List of flattened taxonomy tuples

        Returns:
            Selected topic as (category, topic, subtopic)
        """
        if not flattened_taxonomy:
            logging.warning("No flattened topics available. Using default topic.")
            return ("General", "General Conversation", "")

        if self.topic_distribution == "uniform":
            return self._select_topic_uniform(flattened_taxonomy)
        elif self.topic_distribution == "normal":
            return self._select_topic_normal(flattened_taxonomy)
        elif self.topic_distribution == "custom":
            return self._select_topic_custom(flattened_taxonomy)
        else:
            logging.warning(f"Unknown topic distribution: {self.topic_distribution}. Using uniform distribution.")
            return self._select_topic_uniform(flattened_taxonomy)

    def _select_topic_uniform(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
        """Select a topic using uniform distribution."""
        category, topic, subtopic = random.choice(flattened_taxonomy)
        logging.info(f"Selected topic (uniform): category='{category}', topic='{topic}', subtopic='{subtopic}'")
        return (category, topic, subtopic)

    def _select_topic_normal(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
        """Select a topic using a normal distribution."""
        num_topics = len(flattened_taxonomy)
        if num_topics == 1:
            return flattened_taxonomy[0]

        # Generate a normal distribution centered around the middle index
        mu = (num_topics - 1) / 2  # Center of the distribution
        sigma = num_topics / 6  # Standard deviation (approx. 3 sigma covers most of the range)
        index = int(round(np.random.normal(mu, sigma)))

        # Ensure the index is within bounds
        index = max(0, min(index, num_topics - 1))

        category, topic, subtopic = flattened_taxonomy[index]
        logging.info(f"Selected topic (normal): category='{category}', topic='{topic}', subtopic='{subtopic}'")
        return (category, topic, subtopic)

    def _select_topic_custom(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
        """Select a topic using custom weights."""
        # Build a list of topics and their corresponding weights
        weighted_topics = []
        for category, topic, subtopic in flattened_taxonomy:
            topic_key = f"{category}/{topic}/{subtopic}" if subtopic else f"{category}/{topic}"
            weight = self.topic_weights.get(topic_key, 1.0)  # Default weight is 1.0
            weighted_topics.append(((category, topic, subtopic), weight))

        # Separate topics and weights
        topics, weights = zip(*weighted_topics)

        # Normalize weights to ensure they sum to 1
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            logging.warning("All custom topic weights are zero. Using uniform distribution.")
            return self._select_topic_uniform(flattened_taxonomy)

        # Select a topic based on the normalized weights
        selected_topic = random.choices(topics, weights=normalized_weights, k=1)[0]
        category, topic, subtopic = selected_topic
        logging.info(f"Selected topic (custom): category='{category}', topic='{topic}', subtopic='{subtopic}'")
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