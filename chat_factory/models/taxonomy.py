"""
Models for taxonomy data structures.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TaxonomyTopic:
    """
    Represents a topic in a taxonomy.
    """
    category: str
    topic: str
    subtopic: Optional[str] = None
    
    def get_formatted_topic(self) -> str:
        """
        Returns a formatted topic string, including subtopic if available.
        """
        if self.subtopic:
            return f"{self.topic}.{self.subtopic}"
        return self.topic
    
    def to_tuple(self) -> tuple:
        """
        Convert to a tuple representation (category, topic, subtopic).
        """
        return (self.category, self.topic, self.subtopic or "")


@dataclass
class CompanyTaggingInfo:
    """
    Information about company tagging for a conversation type.
    """
    enabled: bool = False
    company_count_options: List[int] = field(default_factory=list)
    probability: float = 0.8
    min_companies: int = 1
    max_companies: int = 3


@dataclass
class ConversationTypeInfo:
    """
    Metadata for a conversation type.
    """
    description: str = ""
    message_format: str = "formal"
    message_style: str = ""
    typical_message_length: str = "medium"
    example_keywords: List[str] = field(default_factory=list)
    company_tagging: CompanyTaggingInfo = field(default_factory=CompanyTaggingInfo)
    

@dataclass
class Taxonomy:
    """
    Base class for taxonomies.
    """
    name: str
    topics: List[TaxonomyTopic] = field(default_factory=list)
    conversation_types: Dict[str, ConversationTypeInfo] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_flattened_topics(self) -> List[tuple]:
        """
        Get a flattened list of topics as tuples.
        """
        return [topic.to_tuple() for topic in self.topics]