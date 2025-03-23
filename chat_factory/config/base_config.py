"""
Base configuration class for Chat Factory.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class BaseConfig:
    """
    Base configuration with common settings.
    """
    
    # Project metadata
    PROJECT_ID: str
    RUN_ID: Optional[str] = None
    
    # LLM settings
    LLM_PROVIDER: str = "vertex_ai"
    MODEL_NAME: str = "gemini-1.5-flash-002"
    LOCATION: str = "us-central1"  # Added LOCATION parameter
    TEMPERATURE: float = 0.3
    TOP_P: float = 1.0
    TOP_K: int = 40
    
    # Output settings
    OUTPUT_DIR: str = "synthetic_data"
    JSON_VERSION: str = "5"
    
    # Generation settings
    NUM_CONVERSATIONS: int = 20
    MIN_MESSAGES: int = 2
    MAX_MESSAGES: int = 10
    
    # Strategy selection
    TAXONOMY_STRATEGY: str = "financial_advisory"
    GENERATION_STRATEGY: str = "financial_advisory"
    FEW_SHOT_STRATEGY: str = "basic"
    
    # File paths
    TAXONOMY_FILE: str = "taxonomies/financial_advisory.json"
    FEW_SHOT_EXAMPLES_DIR: str = "few_shot_examples"
    CONVERSATION_MANIFEST_DIR: str = "conversation_scripts"
    
    # Common settings for all strategies
    MESSAGE_LENGTH_RATIO: Dict[str, float] = field(default_factory=lambda: {
        "short": 0.4,
        "medium": 0.3,
        "long": 0.3
    })
    
    # Personas and names
    ADVISOR_NAMES: List[str] = field(default_factory=list)
    CLIENT_NAMES: List[str] = field(default_factory=list)
    PERSONAS: List[str] = field(default_factory=list)
    
    # Topic settings
    CONVERSATION_TYPES: List[str] = field(default_factory=list)
    MESSAGE_FORMATS: Dict[str, str] = field(default_factory=dict)
    
    # Company targeting
    COMPANY_DATA_FILE: str = ""
    COMPANY_TARGETING: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "probability": 0.8,
        "min_companies": 1,
        "max_companies": 3
    })
    
    # Distribution settings
    TOPIC_DISTRIBUTION: str = "uniform"
    
    # Logging
    LOG_FILE: str = "synthetic_chat_generator.log"
    
    def __post_init__(self):
        """Validate and normalize config after initialization."""
        # Ensure lists are initialized if they were None
        if self.ADVISOR_NAMES is None:
            self.ADVISOR_NAMES = []
        if self.CLIENT_NAMES is None:
            self.CLIENT_NAMES = []
        if self.PERSONAS is None:
            self.PERSONAS = []
        if self.CONVERSATION_TYPES is None:
            self.CONVERSATION_TYPES = []
        if self.MESSAGE_FORMATS is None:
            self.MESSAGE_FORMATS = {}