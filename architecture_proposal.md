# Chat Factory Architecture Proposal

## Current Architecture Assessment

The current codebase has several challenges:

1. **Tight Coupling**: The `SyntheticChatGenerator` class handles both financial advisory and company tagging use cases with conditional logic
2. **Mixed Concerns**: Configuration, taxonomy processing, and conversation generation logic are intertwined
3. **Limited Extensibility**: Adding a new use case requires modifying core classes
4. **Duplicated Logic**: Similar patterns are reimplemented across use cases

## Proposed Architecture

We propose transforming the codebase into a modular, extensible framework using the Strategy pattern and dependency injection:

```
chat-factory/
├── chat_factory/                  # Core package
│   ├── __init__.py
│   ├── config/                    # Configuration management
│   │   ├── __init__.py
│   │   ├── base_config.py         # Base configuration class
│   │   ├── config_loader.py       # Dynamic config loading
│   │   └── defaults.py            # Default configuration values
│   ├── models/                    # Shared data models
│   │   ├── __init__.py
│   │   ├── conversation.py        # Chat/conversation models
│   │   └── taxonomy.py            # Taxonomy data structures
│   ├── strategies/                # Strategy implementations
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract base classes
│   │   ├── financial_advisory/    # Financial advisory strategies
│   │   │   ├── __init__.py
│   │   │   ├── taxonomy.py        # Financial advisory taxonomy strategy
│   │   │   └── generator.py       # Financial advisory generator strategy
│   │   └── company_tagging/       # Company tagging strategies
│   │       ├── __init__.py
│   │       ├── taxonomy.py        # Company tagging taxonomy strategy
│   │       └── generator.py       # Company tagging generator strategy
│   ├── generator.py               # Main generator orchestration
│   ├── llm/                       # LLM integration
│   │   ├── __init__.py
│   │   ├── vertex_ai.py           # Vertex AI adapter
│   │   └── base.py                # Abstract LLM interface
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── logging.py             # Logging utilities
│       └── file_io.py             # File I/O utilities
├── configs/                       # Configuration files
│   ├── financial_advisory.py      # Financial advisory configuration
│   └── company_tagging.py         # Company tagging configuration
├── taxonomies/                    # Taxonomy definition files
│   ├── financial_advisory.json    # Financial advisory taxonomy
│   └── company_tagging.json       # Company tagging taxonomy
└── main.py                        # Application entry point
```

## Key Components and Interfaces

### 1. Strategy Pattern Implementation

```python
# chat_factory/strategies/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional

class TaxonomyStrategy(ABC):
    """Abstract base class for taxonomy processing strategies."""
    
    @abstractmethod
    def load_taxonomy(self, taxonomy_file: str) -> Dict[str, Any]:
        """Load taxonomy from file."""
        pass
        
    @abstractmethod
    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """Flatten taxonomy into a consistent format."""
        pass
        
    @abstractmethod
    def select_topic(self, flattened_taxonomy: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
        """Select a topic from the flattened taxonomy."""
        pass

class GenerationStrategy(ABC):
    """Abstract base class for conversation generation strategies."""
    
    @abstractmethod
    def create_manifest_blueprint(self, conversation_type: str, topic: Tuple[str, str, str], 
                                  num_messages: int) -> Dict[str, Any]:
        """Create a manifest blueprint for a conversation."""
        pass
        
    @abstractmethod
    def construct_prompt(self, advisor_name: str, client_name: str, 
                         conversation_type: str, num_messages: int, 
                         manifest_blueprint: Dict[str, Any]) -> str:
        """Construct a prompt for conversation generation."""
        pass
        
    @abstractmethod
    def process_llm_response(self, llm_response: str) -> List[Dict[str, str]]:
        """Process LLM response into standardized conversation format."""
        pass
```

### 2. Configuration Management

```python
# chat_factory/config/base_config.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class BaseConfig:
    """Base configuration with common settings."""
    
    # Project metadata
    PROJECT_ID: str
    RUN_ID: Optional[str] = None
    
    # LLM settings
    LLM_PROVIDER: str = "vertex_ai"
    MODEL_NAME: str = "gemini-1.5-flash-002"
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
    
    # File paths
    TAXONOMY_FILE: str = "taxonomies/financial_advisory.json"
    FEW_SHOT_EXAMPLES_DIR: str = "few_shot_examples"
    CONVERSATION_MANIFEST_DIR: str = "conversation_scripts"
    
    # Additional settings specific to all strategies
    MESSAGE_LENGTH_RATIO: Dict[str, float] = field(default_factory=lambda: {
        "short": 0.4,
        "medium": 0.3,
        "long": 0.3
    })
```

### 3. Main Generator Class

```python
# chat_factory/generator.py
import logging
from typing import Dict, Any, List, Optional, Type, Tuple
from .strategies.base import TaxonomyStrategy, GenerationStrategy
from .llm.base import LLMProvider
from .models.conversation import ConversationFile, SingleConversation, ChatLine
from .config.base_config import BaseConfig

class SyntheticChatGenerator:
    """Main generator class that orchestrates the generation process."""
    
    def __init__(self, 
                 config: BaseConfig,
                 taxonomy_strategy: TaxonomyStrategy,
                 generation_strategy: GenerationStrategy,
                 llm_provider: LLMProvider):
        """
        Initialize the generator with strategies and config.
        
        Args:
            config: Configuration settings
            taxonomy_strategy: Strategy for taxonomy processing
            generation_strategy: Strategy for conversation generation
            llm_provider: Provider for LLM integration
        """
        self.config = config
        self.taxonomy_strategy = taxonomy_strategy
        self.generation_strategy = generation_strategy
        self.llm_provider = llm_provider
        
        # Initialize resources
        self.taxonomy = self.taxonomy_strategy.load_taxonomy(config.TAXONOMY_FILE)
        self.flattened_topics = self.taxonomy_strategy.flatten_taxonomy(self.taxonomy)
        self.conversation_buffer = {}
        
        # Setup logging and output directories
        self.setup_logging()
        self.setup_output_directories()
        
    async def process_conversation(self, conv_number: int, conversation_type: str, 
                                  advisor_name: str, client_name: str, 
                                  num_messages: int) -> SingleConversation:
        """Process a single conversation."""
        
        # Select topic using the taxonomy strategy
        category, topic, subtopic = self.taxonomy_strategy.select_topic(self.flattened_topics)
        
        # Create manifest blueprint using the generation strategy
        manifest_blueprint = self.generation_strategy.create_manifest_blueprint(
            conversation_type, (category, topic, subtopic), num_messages
        )
        
        # Construct prompt for LLM
        prompt = self.generation_strategy.construct_prompt(
            advisor_name, client_name, conversation_type, 
            num_messages, manifest_blueprint
        )
        
        # Generate conversation using LLM
        llm_response = await self.llm_provider.generate_content(prompt)
        
        # Process LLM response
        conversation_lines = self.generation_strategy.process_llm_response(llm_response)
        
        # Create conversation object
        formatted_topic = f"{topic}.{subtopic}" if subtopic else topic
        conversation_id = f"{self.config.RUN_ID}_{conv_number}_{uuid.uuid4().hex[:8]}"
        
        conversation = SingleConversation(
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            category=category,
            topic=formatted_topic,
            lines=[ChatLine(**line) for line in conversation_lines],
            company_mentions=manifest_blueprint.get("key_companies", [])
        )
        
        return conversation
    
    async def generate_synthetic_data(self):
        """Main method to generate synthetic data."""
        # Implementation details...
```

### 4. Factory for Creating Strategies

```python
# chat_factory/strategies/__init__.py
from typing import Dict, Type
from .base import TaxonomyStrategy, GenerationStrategy
from .financial_advisory.taxonomy import FinancialAdvisoryTaxonomyStrategy
from .financial_advisory.generator import FinancialAdvisoryGenerationStrategy
from .company_tagging.taxonomy import CompanyTaggingTaxonomyStrategy
from .company_tagging.generator import CompanyTaggingGenerationStrategy

# Registry of available strategies
TAXONOMY_STRATEGIES: Dict[str, Type[TaxonomyStrategy]] = {
    "financial_advisory": FinancialAdvisoryTaxonomyStrategy,
    "company_tagging": CompanyTaggingTaxonomyStrategy
}

GENERATION_STRATEGIES: Dict[str, Type[GenerationStrategy]] = {
    "financial_advisory": FinancialAdvisoryGenerationStrategy,
    "company_tagging": CompanyTaggingGenerationStrategy
}

def create_taxonomy_strategy(strategy_name: str, config: 'BaseConfig') -> TaxonomyStrategy:
    """Factory function to create a taxonomy strategy."""
    if strategy_name not in TAXONOMY_STRATEGIES:
        raise ValueError(f"Unknown taxonomy strategy: {strategy_name}")
    return TAXONOMY_STRATEGIES[strategy_name](config)

def create_generation_strategy(strategy_name: str, config: 'BaseConfig') -> GenerationStrategy:
    """Factory function to create a generation strategy."""
    if strategy_name not in GENERATION_STRATEGIES:
        raise ValueError(f"Unknown generation strategy: {strategy_name}")
    return GENERATION_STRATEGIES[strategy_name](config)
```

## 5. Main Application Entry Point

```python
# main.py
import asyncio
import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any

from chat_factory.config.base_config import BaseConfig
from chat_factory.strategies import create_taxonomy_strategy, create_generation_strategy
from chat_factory.llm import create_llm_provider
from chat_factory.generator import SyntheticChatGenerator

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, help="Optional run id to use for this generation")
    parser.add_argument("--config", type=str, default="config.py", 
                        help="Path to config file to use instead of default config.py")
    return parser.parse_args()

def load_config_from_file(file_path: str) -> Dict[str, Any]:
    """Load configuration from a Python file."""
    spec = importlib.util.spec_from_file_location("config_module", file_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    # Extract configuration values
    config_dict = {key: value for key, value in vars(config_module).items() 
                  if not key.startswith('__') and key.isupper()}
    return config_dict

async def main():
    args = parse_arguments()
    
    # Load configuration
    config_dict = load_config_from_file(args.config)
    
    # Override run_id if provided
    if args.run_id:
        config_dict['RUN_ID'] = args.run_id
    
    # Create configuration object
    config = BaseConfig(**config_dict)
    
    # Create strategies
    taxonomy_strategy = create_taxonomy_strategy(config.TAXONOMY_STRATEGY, config)
    generation_strategy = create_generation_strategy(config.GENERATION_STRATEGY, config)
    llm_provider = create_llm_provider(config.LLM_PROVIDER, config)
    
    # Create generator
    generator = SyntheticChatGenerator(
        config=config,
        taxonomy_strategy=taxonomy_strategy,
        generation_strategy=generation_strategy,
        llm_provider=llm_provider
    )
    
    # Run generation
    await generator.generate_synthetic_data()

if __name__ == "__main__":
    asyncio.run(main())
```

## Benefits of This Architecture

1. **Separation of Concerns**: Each component has a single responsibility
2. **Extensibility**: New strategies can be added without modifying existing code
3. **Testability**: Components can be tested in isolation
4. **Configuration Clarity**: Clear separation between core configuration and use-case specific settings
5. **Reduced Duplication**: Common functionality centralized in base classes
6. **Explicit Dependencies**: Dependencies are injected rather than hardcoded

## Implementation Plan

1. Create the base classes and interfaces
2. Implement the financial advisory strategy
3. Implement the company tagging strategy
4. Develop the main generator class
5. Build the configuration management system
6. Create the factory methods
7. Update the main.py entry point
8. Write tests for each component

This refactoring will maintain all current functionality while making the codebase more maintainable, extensible, and resilient to changes in requirements.