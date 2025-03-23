"""
Models for conversation data structures.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ChatLine:
    """
    Represents a single line of conversation with speaker, text, and timestamp.
    """
    speaker: str  # "0" = client, "1" = advisor
    text: str
    timestamp: str = None  # ISO format timestamp


@dataclass
class SingleConversation:
    """
    Represents a single conversation with metadata and chat lines.
    """
    conversation_id: str
    timestamp: str
    category: str  # Top-level category
    topic: str     # Will now contain "topic.subtopic" if applicable
    lines: List[ChatLine] = field(default_factory=list)
    company_mentions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the conversation to a dictionary for serialization.
        """
        return {
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "topic": self.topic,
            "lines": [line.__dict__ for line in self.lines],
            "company_mentions": self.company_mentions
        }


@dataclass
class ConversationFile:
    """
    Represents a file containing multiple conversations between the same advisor and client.
    """
    version: str
    advisor: str
    client: str
    conversations: List[SingleConversation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the conversation file to a dictionary for serialization.
        """
        return {
            "version": self.version,
            "advisor": self.advisor,
            "client": self.client,
            "conversations": [conv.to_dict() for conv in self.conversations]
        }