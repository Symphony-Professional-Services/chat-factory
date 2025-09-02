"""
Taxonomy strategy for company tagging use case.
"""

import json
import logging
import random
from typing import List, Dict, Any, Tuple
from pathlib import Path

from ...models.taxonomy import Taxonomy, TaxonomyTopic, ConversationTypeInfo, CompanyTaggingInfo
from ..base import TaxonomyStrategy


class CompanyTaggingTaxonomyStrategy(TaxonomyStrategy):
    """
    Implementation of taxonomy strategy for company tagging conversations.
    
    This strategy handles taxonomies for company-focused conversations, which 
    include explicit settings for company tagging in different conversation types.
    """
    
    def __init__(self, config):
        """
        Initialize the company tagging taxonomy strategy.
        
        Args:
            config: Configuration with taxonomy settings
        """
        super().__init__(config)
        self.topic_distribution = getattr(config, 'TOPIC_DISTRIBUTION', 'uniform')
    
    def load_taxonomy(self, taxonomy_file: str) -> Taxonomy:
        """
        Load and parse company tagging taxonomy from file.
        
        Args:
            taxonomy_file: Path to the taxonomy file
            
        Returns:
            Parsed Taxonomy object
        """
        logging.info(f"Loading company tagging taxonomy from: {taxonomy_file}")
        
        try:
            with open(taxonomy_file, 'r') as f:
                raw_taxonomy = json.load(f)
            
            # Validate the taxonomy structure
            if not raw_taxonomy:
                logging.error(f"Empty taxonomy loaded from {taxonomy_file}")
                return Taxonomy(name="empty")
            
            taxonomy = Taxonomy(
                name="company_tagging",
                raw_data=raw_taxonomy
            )
            
            # Process the raw taxonomy into structured topics
            taxonomy.topics = self._extract_topics(raw_taxonomy)
            
            # If this is a company tagging taxonomy, process conversation types
            taxonomy_format = self.detect_taxonomy_format(raw_taxonomy)
            if taxonomy_format == "company_tagging" and "conversation_types" in raw_taxonomy:
                self._process_conversation_types(taxonomy, raw_taxonomy)
            
            logging.info(f"Successfully loaded company tagging taxonomy with {len(taxonomy.topics)} topics")
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
        
        # Skip the conversation_types dictionary if present
        taxonomy_items = {k: v for k, v in raw_taxonomy.items() if k != "conversation_types"}
        
        for category, items in taxonomy_items.items():
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
    
    def _process_conversation_types(self, taxonomy: Taxonomy, raw_taxonomy: Dict[str, Any]):
        """
        Process conversation types configuration from raw taxonomy.
        
        Args:
            taxonomy: Taxonomy object to update
            raw_taxonomy: Raw taxonomy data
        """
        if "conversation_types" not in raw_taxonomy:
            return
            
        conversation_types = raw_taxonomy["conversation_types"]
        
        for conv_type, data in conversation_types.items():
            company_tagging_info = CompanyTaggingInfo(
                enabled=data.get("company_tagging", {}).get("enabled", True),
                company_count_options=data.get("company_tagging", {}).get("company_count_options", [1, 2, 3]),
                probability=data.get("company_tagging", {}).get("probability", 0.8),
                min_companies=data.get("company_tagging", {}).get("min_companies", 1),
                max_companies=data.get("company_tagging", {}).get("max_companies", 3)
            )
            
            conv_type_info = ConversationTypeInfo(
                description=data.get("description", ""),
                message_format=data.get("message_format", "formal"),
                message_style=data.get("message_style", ""),
                typical_message_length=data.get("typical_message_length", "medium"),
                example_keywords=data.get("example_keywords", []),
                company_tagging=company_tagging_info
            )
            
            taxonomy.conversation_types[conv_type] = conv_type_info
    
    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        Flatten taxonomy into a consistent format.
        
        Args:
            taxonomy: Raw taxonomy data
            
        Returns:
            List of tuples in the format (category, topic, subtopic)
        """
        flattened = []
        
        # Skip the conversation_types dictionary if present
        taxonomy_items = {k: v for k, v in taxonomy.items() if k != "conversation_types"}
        
        for category, items in taxonomy_items.items():
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
        
        logging.info(f"Flattened company tagging taxonomy into {len(flattened)} unique topic paths")
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
            return ("Market Commentary", "General Market Update", "")
        
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