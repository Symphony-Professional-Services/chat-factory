"""
Main generator class for Chat Factory.
"""

import logging
import json
import uuid
import random
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .models.conversation import ConversationFile, SingleConversation, ChatLine
from .strategies.base import TaxonomyStrategy, GenerationStrategy, FewShotExampleStrategy
from .llm.base import LLMProvider
from .config.base_config import BaseConfig
from .utils import ensure_directory, sanitize_filename


class SyntheticChatGenerator:
    """
    Main generator class that orchestrates the synthetic conversation generation process.
    """
    
    def __init__(self, 
                 config: BaseConfig,
                 taxonomy_strategy: TaxonomyStrategy,
                 generation_strategy: GenerationStrategy,
                 few_shot_strategy: FewShotExampleStrategy,
                 llm_provider: LLMProvider):
        """
        Initialize the generator with strategies and config.
        
        Args:
            config: Configuration settings
            taxonomy_strategy: Strategy for taxonomy processing
            generation_strategy: Strategy for conversation generation
            few_shot_strategy: Strategy for few-shot examples
            llm_provider: Provider for LLM integration
        """
        self.config = config
        self.taxonomy_strategy = taxonomy_strategy
        self.generation_strategy = generation_strategy
        self.few_shot_strategy = few_shot_strategy
        self.llm_provider = llm_provider
        
        # Generate or use run_id
        self.run_id = config.RUN_ID or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        logging.info(f"Using run_id: {self.run_id}")
        
        # Initialize resources
        self.taxonomy = self.taxonomy_strategy.load_taxonomy(config.TAXONOMY_FILE)
        self.flattened_topics = self.taxonomy_strategy.flatten_taxonomy(self.taxonomy.raw_data)
        self.conversation_buffer = {}
        
        # Setup output directories
        self.output_dir = self.setup_output_directory()
        
        # Initialize conversation manifest logger
        try:
            self.manifest_logger = self.setup_manifest_logger()
        except Exception as e:
            logging.warning(f"Could not set up manifest logger: {e}. Conversation manifests will not be saved.")
            self.manifest_logger = None
    
    def setup_output_directory(self) -> Path:
        """
        Set up the output directory for generated conversations.
        
        Returns:
            Path to the output directory
        """
        output_dir = Path(self.config.OUTPUT_DIR) / self.run_id
        ensure_directory(str(output_dir))
        logging.info(f"Created output directory: {output_dir}")
        return output_dir
    
    def setup_manifest_logger(self) -> logging.Logger:
        """
        Set up a logger for conversation manifests.
        
        Returns:
            Configured logger for manifests
        """
        manifest_dir = Path(self.config.CONVERSATION_MANIFEST_DIR)
        
        try:
            # Try to create the directory if it doesn't exist
            manifest_dir.mkdir(parents=True, exist_ok=True)
            
            manifest_logger = logging.getLogger("conversation_manifest")
            manifest_logger.setLevel(logging.INFO)
            
            # Remove all handlers first (to handle test mocks properly)
            for handler in manifest_logger.handlers[:]:
                manifest_logger.removeHandler(handler)
                # Close the handler to prevent resource warnings
                if hasattr(handler, 'close'):
                    handler.close()
                
            manifest_log_file = manifest_dir / f"conversation_manifest_{self.run_id}.log"
            handler = logging.FileHandler(manifest_log_file)
            handler.setFormatter(logging.Formatter('%(message)s'))
            manifest_logger.addHandler(handler)
            
            return manifest_logger
        except (PermissionError, OSError) as e:
            # If we can't create the directory or file, try using a temporary directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "chat_factory_manifests"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            manifest_logger = logging.getLogger("conversation_manifest")
            manifest_logger.setLevel(logging.INFO)
            
            # Remove all handlers first (to handle test mocks properly)
            for handler in manifest_logger.handlers[:]:
                manifest_logger.removeHandler(handler)
                # Close the handler to prevent resource warnings
                if hasattr(handler, 'close'):
                    handler.close()
                
            manifest_log_file = temp_dir / f"conversation_manifest_{self.run_id}.log"
            handler = logging.FileHandler(manifest_log_file)
            handler.setFormatter(logging.Formatter('%(message)s'))
            manifest_logger.addHandler(handler)
            
            logging.warning(f"Using temporary directory for manifest logs: {temp_dir}")
            return manifest_logger
    
    async def process_conversation(self, conv_number: int, conversation_type: str, 
                                  advisor_name: str, client_name: str, 
                                  num_messages: int) -> SingleConversation:
        """
        Process a single conversation.
        
        Args:
            conv_number: Sequence number for this conversation
            conversation_type: Type of conversation to generate
            advisor_name: Name of the advisor
            client_name: Name of the client
            num_messages: Number of messages to generate
            
        Returns:
            Generated conversation
        """
        # Select topic using the taxonomy strategy
        category, topic, subtopic = self.taxonomy_strategy.select_topic(self.flattened_topics)
        
        # Create manifest blueprint using the generation strategy
        manifest_blueprint = self.generation_strategy.create_manifest_blueprint(
            conversation_type, (category, topic, subtopic), num_messages
        )
        
        # Get few-shot examples based on conversation characteristics
        few_shot_examples = await self.few_shot_strategy.get_examples(
            conversation_type, category, topic, subtopic
        )
        
        # Construct prompt for LLM
        prompt = await self.generation_strategy.construct_prompt(
            advisor_name, client_name, conversation_type, 
            num_messages, manifest_blueprint, few_shot_examples
        )
        
        # Generate conversation using LLM with retry logic
        llm_response = await self.llm_provider.retry_with_backoff(prompt)
        
        if not llm_response:
            logging.error(f"Failed to generate conversation {conv_number} after multiple retries")
            return None
        
        # Process LLM response
        conversation_lines = self.generation_strategy.process_llm_response(llm_response)
        
        # Create conversation object
        formatted_topic = f"{topic}.{subtopic}" if subtopic else topic
        conversation_id = f"{self.run_id}_{conv_number}_{uuid.uuid4().hex[:8]}"
        
        conversation = SingleConversation(
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            category=category,
            topic=formatted_topic,
            lines=[ChatLine(**line) for line in conversation_lines],
            company_mentions=manifest_blueprint.get("key_companies", [])
        )
        
        # Log manifest information
        self.log_conversation_manifest(
            conv_number, conversation_id, advisor_name, client_name,
            category, topic, subtopic, manifest_blueprint
        )
        
        logging.debug(f"Generated conversation {conversation_id} for {advisor_name}-{client_name} with {len(conversation_lines)} messages")
        
        return conversation
    
    def log_conversation_manifest(self, conv_number: int, conversation_id: str,
                                 advisor_name: str, client_name: str,
                                 category: str, topic: str, subtopic: str,
                                 manifest_blueprint: Dict[str, Any]):
        """
        Log conversation manifest information for tracking and analysis.
        
        Args:
            conv_number: Sequence number for this conversation
            conversation_id: Unique ID for the conversation
            advisor_name: Name of the advisor
            client_name: Name of the client
            category: Conversation category
            topic: Conversation topic
            subtopic: Conversation subtopic
            manifest_blueprint: Blueprint for the conversation
        """
        if self.manifest_logger is None:
            return
            
        manifest_data = {
            "conversation_id": conversation_id,
            "conv_number": conv_number,
            "advisor": advisor_name,
            "client": client_name,
            "category": category,
            "topic": topic,
            "subtopic": subtopic,
            "timestamp": datetime.now().isoformat(),
            "company_targeting_enabled": manifest_blueprint.get("company_targeting_enabled", False),
            "key_companies": manifest_blueprint.get("key_companies", [])
        }
        
        self.manifest_logger.info(json.dumps(manifest_data))
    
    def save_conversation_file(self, advisor_name: str, client_name: str, 
                              conversation_file: ConversationFile):
        """
        Save a conversation file to disk.
        
        Args:
            advisor_name: Name of the advisor
            client_name: Name of the client
            conversation_file: ConversationFile to save
        """
        # Create sanitized filename
        sanitized_advisor = sanitize_filename(advisor_name)
        sanitized_client = sanitize_filename(client_name)
        filename = f"{sanitized_advisor}_{sanitized_client}_{uuid.uuid4().hex[:6]}.json"
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(conversation_file.to_dict(), f, indent=2)
        
        logging.info(f"Saved conversation file: {file_path}")
    
    def select_advisors_clients(self) -> Tuple[str, str]:
        """
        Select a random advisor-client pair from available names.
        
        Returns:
            Tuple of (advisor_name, client_name)
        """
        advisor = random.choice(self.config.ADVISOR_NAMES)
        client = random.choice(self.config.CLIENT_NAMES)
        logging.debug(f"Selected advisor-client pair: {advisor} - {client}")
        return advisor, client
    
    def select_conversation_type(self) -> str:
        """
        Select a random conversation type from available types.
        
        Returns:
            Selected conversation type
        """
        conversation_type = random.choice(self.config.CONVERSATION_TYPES)
        logging.debug(f"Selected conversation type: {conversation_type}")
        return conversation_type
    
    async def generate_synthetic_data(self):
        """
        Main method to generate synthetic data.
        
        This orchestrates the entire process of generating multiple conversations
        according to the configuration.
        """
        logging.info(f"Starting synthetic data generation with run_id: {self.run_id}")
        logging.info(f"Generating {self.config.NUM_CONVERSATIONS} conversations")
        
        # Initialize the LLM provider
        await self.llm_provider.initialize()
        
        # Track conversation pairing to group multiple conversations between the same people
        self.conversation_buffer = {}
        
        for i in range(1, self.config.NUM_CONVERSATIONS + 1):
            try:
                advisor_name, client_name = self.select_advisors_clients()
                conversation_type = self.select_conversation_type()
                
                # Determine number of messages for this conversation
                num_messages = random.randint(self.config.MIN_MESSAGES, self.config.MAX_MESSAGES)
                
                # Generate the conversation
                conversation = await self.process_conversation(
                    conv_number=i,
                    conversation_type=conversation_type,
                    advisor_name=advisor_name,
                    client_name=client_name,
                    num_messages=num_messages
                )
                
                if not conversation:
                    logging.warning(f"Failed to generate conversation {i}, skipping")
                    continue
                
                # Add to conversation buffer (for grouping)
                buffer_key = f"{advisor_name}_{client_name}"
                if buffer_key not in self.conversation_buffer:
                    self.conversation_buffer[buffer_key] = ConversationFile(
                        version=self.config.JSON_VERSION,
                        advisor=advisor_name,
                        client=client_name,
                        conversations=[]
                    )
                
                self.conversation_buffer[buffer_key].conversations.append(conversation)
                
                # Save after every few conversations or when buffer gets too large
                if i % 5 == 0 or len(self.conversation_buffer[buffer_key].conversations) >= 10:
                    self.save_conversation_file(
                        advisor_name, client_name, self.conversation_buffer[buffer_key]
                    )
                    # Clear buffer after saving
                    self.conversation_buffer[buffer_key].conversations = []
                
                # Progress update
                if i % 10 == 0:
                    logging.info(f"Generated {i}/{self.config.NUM_CONVERSATIONS} conversations")
                
            except Exception as e:
                logging.error(f"Error generating conversation {i}: {e}", exc_info=True)
        
        # Save any remaining conversations in the buffer
        for buffer_key, conversation_file in self.conversation_buffer.items():
            if conversation_file.conversations:
                advisor_name, client_name = buffer_key.split('_', 1)
                self.save_conversation_file(advisor_name, client_name, conversation_file)
        
        logging.info(f"Completed synthetic data generation. Generated {self.config.NUM_CONVERSATIONS} conversations.")