# """
# Main generator class for Chat Factory.
# """

# import logging
# import json
# import uuid
# import random
# import asyncio
# import os
# from datetime import datetime, timedelta
# from pathlib import Path
# from typing import Dict, Any, List, Optional, Tuple

# from .models.conversation import ConversationFile, SingleConversation, ChatLine
# from .strategies.base import TaxonomyStrategy, GenerationStrategy, FewShotExampleStrategy
# from .strategies.base.datetime_strategy import DatetimeStrategy
# from .llm.base import LLMProvider
# from .config.base_config import BaseConfig
# from .utils import ensure_directory, sanitize_filename


# class SyntheticChatGenerator:
#     """
#     Main generator class that orchestrates the synthetic conversation generation process.
#     """
    
#     def __init__(self, 
#                  config: BaseConfig,
#                  taxonomy_strategy: TaxonomyStrategy,
#                  generation_strategy: GenerationStrategy,
#                  few_shot_strategy: FewShotExampleStrategy,
#                  llm_provider: LLMProvider,
#                  datetime_strategy: Optional[DatetimeStrategy] = None):
#         """
#         Initialize the generator with strategies and config.
        
#         Args:
#             config: Configuration settings
#             taxonomy_strategy: Strategy for taxonomy processing
#             generation_strategy: Strategy for conversation generation
#             few_shot_strategy: Strategy for few-shot examples
#             llm_provider: Provider for LLM integration
#             datetime_strategy: Optional strategy for temporal distribution
#         """
#         self.config = config
#         self.taxonomy_strategy = taxonomy_strategy
#         self.generation_strategy = generation_strategy
#         self.few_shot_strategy = few_shot_strategy
#         self.llm_provider = llm_provider
#         self.datetime_strategy = datetime_strategy
        
#         # Generate or use run_id
#         self.run_id = config.RUN_ID or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
#         logging.info(f"Using run_id: {self.run_id}")
        
#         # Initialize resources
#         self.taxonomy = self.taxonomy_strategy.load_taxonomy(config.TAXONOMY_FILE)
#         self.flattened_topics = self.taxonomy_strategy.flatten_taxonomy(self.taxonomy.raw_data)
#         self.conversation_buffer = {}
        
#         # Setup output directories
#         self.output_dir = self.setup_output_directory()
        
#         # Initialize client-advisor distribution
#         self.initialize_client_advisor_map()
        
#         # Initialize conversation manifest logger
#         try:
#             self.manifest_logger = self.setup_manifest_logger()
#         except Exception as e:
#             logging.warning(f"Could not set up manifest logger: {e}. Conversation manifests will not be saved.")
#             self.manifest_logger = None
            
#         # Track all timestamps for distribution analysis
#         self.all_timestamps = []
    
#     def setup_output_directory(self) -> Path:
#         """
#         Set up the output directory for generated conversations.
        
#         Returns:
#             Path to the output directory
#         """
#         output_dir = Path(self.config.OUTPUT_DIR) / self.run_id
#         ensure_directory(str(output_dir))
#         logging.info(f"Created output directory: {output_dir}")
#         return output_dir
    
#     def setup_manifest_logger(self) -> logging.Logger:
#         """
#         Set up a logger for conversation manifests.
        
#         Returns:
#             Configured logger for manifests
#         """
#         manifest_dir = Path(self.config.CONVERSATION_MANIFEST_DIR)
        
#         try:
#             # Try to create the directory if it doesn't exist
#             manifest_dir.mkdir(parents=True, exist_ok=True)
            
#             manifest_logger = logging.getLogger("conversation_manifest")
#             manifest_logger.setLevel(logging.INFO)
            
#             # Remove all handlers first (to handle test mocks properly)
#             for handler in manifest_logger.handlers[:]:
#                 manifest_logger.removeHandler(handler)
#                 # Close the handler to prevent resource warnings
#                 if hasattr(handler, 'close'):
#                     handler.close()
                
#             manifest_log_file = manifest_dir / f"conversation_manifest_{self.run_id}.log"
#             handler = logging.FileHandler(manifest_log_file)
#             handler.setFormatter(logging.Formatter('%(message)s'))
#             manifest_logger.addHandler(handler)
            
#             return manifest_logger
#         except (PermissionError, OSError) as e:
#             # If we can't create the directory or file, try using a temporary directory
#             import tempfile
#             temp_dir = Path(tempfile.gettempdir()) / "chat_factory_manifests"
#             temp_dir.mkdir(parents=True, exist_ok=True)
            
#             manifest_logger = logging.getLogger("conversation_manifest")
#             manifest_logger.setLevel(logging.INFO)
            
#             # Remove all handlers first (to handle test mocks properly)
#             for handler in manifest_logger.handlers[:]:
#                 manifest_logger.removeHandler(handler)
#                 # Close the handler to prevent resource warnings
#                 if hasattr(handler, 'close'):
#                     handler.close()
                
#             manifest_log_file = temp_dir / f"conversation_manifest_{self.run_id}.log"
#             handler = logging.FileHandler(manifest_log_file)
#             handler.setFormatter(logging.Formatter('%(message)s'))
#             manifest_logger.addHandler(handler)
            
#             logging.warning(f"Using temporary directory for manifest logs: {temp_dir}")
#             return manifest_logger
    
#     async def process_conversation(self, conv_number: int, conversation_type: str, 
#                                   advisor_name: str, client_name: str, 
#                                   num_messages: int) -> SingleConversation:
#         """
#         Process a single conversation.
        
#         Args:
#             conv_number: Sequence number for this conversation
#             conversation_type: Type of conversation to generate
#             advisor_name: Name of the advisor
#             client_name: Name of the client
#             num_messages: Number of messages to generate
            
#         Returns:
#             Generated conversation
#         """
#         # Select topic using the taxonomy strategy
#         category, topic, subtopic = self.taxonomy_strategy.select_topic(self.flattened_topics)
        
#         # Create manifest blueprint using the generation strategy
#         manifest_blueprint = self.generation_strategy.create_manifest_blueprint(
#             conversation_type, (category, topic, subtopic), num_messages
#         )
        
#         # Get few-shot examples based on conversation characteristics
#         few_shot_examples = await self.few_shot_strategy.get_examples(
#             conversation_type, category, topic, subtopic
#         )
        
#         # Construct prompt for LLM
#         prompt = await self.generation_strategy.construct_prompt(
#             advisor_name, client_name, conversation_type, 
#             num_messages, manifest_blueprint, few_shot_examples
#         )
        
#         # Generate conversation using LLM with retry logic
#         llm_response = await self.llm_provider.retry_with_backoff(prompt)
        
#         if not llm_response:
#             logging.error(f"Failed to generate conversation {conv_number} after multiple retries")
#             return None
        
#         # Process LLM response
#         conversation_lines = self.generation_strategy.process_llm_response(llm_response)
        
#         # Create conversation object
#         formatted_topic = f"{topic}.{subtopic}" if subtopic else topic
#         conversation_id = f"{self.run_id}_{conv_number}_{uuid.uuid4().hex[:8]}"
        
#         # Generate conversation timestamp using datetime strategy if available
#         if self.datetime_strategy:
#             conversation_timestamp = self.datetime_strategy.generate_conversation_timestamp(conv_number)
#         else:
#             conversation_timestamp = datetime.now().isoformat()
            
#         # Track timestamp for distribution analysis
#         self.all_timestamps.append(conversation_timestamp)
        
#         # Create basic chat lines
#         chat_lines = [ChatLine(**line) for line in conversation_lines]
        
#         # Apply message timestamps if datetime strategy is available
#         if self.datetime_strategy:
#             message_timestamps = self.datetime_strategy.generate_message_timestamps(
#                 conversation_timestamp, len(chat_lines)
#             )
#             chat_lines = self.datetime_strategy.apply_timestamps_to_conversation(
#                 chat_lines, message_timestamps
#             )
            
#         # Analyze company mentions in the conversation if company targeting is enabled
#         company_mentions = []  # Start with an empty list by default
#         if hasattr(self.generation_strategy, 'check_company_mentions') and hasattr(self.generation_strategy, 'company_targeting'):
#             # Only check for company mentions when targeting is explicitly enabled for THIS conversation
#             if manifest_blueprint.get("company_targeting_enabled", False):
#                 # Start with companies targeted in the prompt
#                 company_mentions = manifest_blueprint.get("key_companies", [])
                
#                 # Convert chat_lines back to the format expected by check_company_mentions
#                 formatted_lines = [{"speaker": line.speaker, "text": line.text} for line in chat_lines]
#                 mention_results = self.generation_strategy.check_company_mentions(formatted_lines)
                
#                 # Only log at DEBUG level for individual conversations to avoid console clutter
#                 company_tag = "[COMPANY METRICS]"
#                 # Log details about company mentions
#                 if mention_results["has_company_mentions"]:
#                     logging.debug(f"{company_tag} Conversation {conv_number}: {mention_results['total_mentions']} " +
#                                f"mentions of {len(mention_results['companies_found'])} companies")
                    
#                     # Log individual companies found at debug level
#                     companies_str = ", ".join(mention_results["companies_found"])
#                     logging.debug(f"{company_tag} Companies found: {companies_str}")
                    
#                     # Use the actual companies found in the text
#                     company_mentions = mention_results["companies_found"]
#                 else:
#                     # Log when companies were targeted but not found (warnings are kept)
#                     target_companies = ", ".join(company_mentions)
#                     logging.debug(f"{company_tag} No company mentions found despite targeting: {target_companies}")
#             else:
#                 # For non-targeted conversations, explicitly log that we're not expecting companies
#                 logging.debug(f"[COMPANY METRICS] Conversation {conv_number}: Company targeting disabled - no companies expected")
                
#         conversation = SingleConversation(
#             conversation_id=conversation_id,
#             timestamp=conversation_timestamp,
#             category=category,
#             topic=formatted_topic,
#             lines=chat_lines,
#             company_mentions=company_mentions
#         )
        
#         # Log manifest information
#         self.log_conversation_manifest(
#             conv_number, conversation_id, advisor_name, client_name,
#             category, topic, subtopic, manifest_blueprint, conversation
#         )
        
#         # Enhanced time-related logging
#         conv_date = datetime.fromisoformat(conversation.timestamp)
        
#         # Calculate time elapsed for the conversation
#         if len(chat_lines) > 1 and all(line.timestamp for line in chat_lines):
#             first_msg_time = datetime.fromisoformat(chat_lines[0].timestamp)
#             last_msg_time = datetime.fromisoformat(chat_lines[-1].timestamp)
#             elapsed_seconds = (last_msg_time - first_msg_time).total_seconds()
#             elapsed_str = f"{int(elapsed_seconds // 60)}m {int(elapsed_seconds % 60)}s"
#         else:
#             elapsed_str = "N/A"
            
#         logging.info(f"Conversation {conv_number}: {conversation_id} | "
#                     f"Date: {conv_date.strftime('%Y-%m-%d')} ({conv_date.strftime('%A')}) | "
#                     f"Time: {conv_date.strftime('%H:%M:%S')} | "
#                     f"Messages: {len(chat_lines)} | Elapsed: {elapsed_str}")
        
#         logging.debug(f"Generated conversation {conversation_id} for {advisor_name}-{client_name} with {len(conversation_lines)} messages")
        
#         return conversation
    
#     def log_conversation_manifest(self, conv_number: int, conversation_id: str,
#                                  advisor_name: str, client_name: str,
#                                  category: str, topic: str, subtopic: str,
#                                  manifest_blueprint: Dict[str, Any],
#                                  conversation: SingleConversation):
#         """
#         Log conversation manifest information for tracking and analysis.
        
#         Args:
#             conv_number: Sequence number for this conversation
#             conversation_id: Unique ID for the conversation
#             advisor_name: Name of the advisor
#             client_name: Name of the client
#             category: Conversation category
#             topic: Conversation topic
#             subtopic: Conversation subtopic
#             manifest_blueprint: Blueprint for the conversation
#             conversation: Generated conversation object
#         """
#         if self.manifest_logger is None:
#             return
        
#         # Track client-advisor pairing for analytics
#         if not hasattr(self, 'advisor_client_interactions'):
#             self.advisor_client_interactions = {}
            
#         pair_key = f"{advisor_name}|{client_name}"
#         if pair_key not in self.advisor_client_interactions:
#             self.advisor_client_interactions[pair_key] = 0
#         self.advisor_client_interactions[pair_key] += 1
        
#         # Company mention data (from generation_strategy.check_company_mentions results)
#         company_mention_count = 0
#         company_mentions_by_name = {}
#         companies_found = []
#         has_company_mentions = False
        
#         # Only track company metrics when targeting was explicitly enabled for this conversation
#         if manifest_blueprint.get("company_targeting_enabled", False):
#             # Check if company_mentions is populated
#             if hasattr(conversation, 'company_mentions') and conversation.company_mentions:
#                 companies_found = conversation.company_mentions
#                 has_company_mentions = True
#                 # For each found company, add it to the count
#                 for company in companies_found:
#                     if company not in company_mentions_by_name:
#                         company_mentions_by_name[company] = 0
#                     company_mentions_by_name[company] += 1
#                     company_mention_count += 1
        
#         # Track company metrics data
#         manifest_data = {
#             "conversation_id": conversation_id,
#             "conv_number": conv_number,
#             "advisor": advisor_name,
#             "client": client_name,
#             "category": category,
#             "topic": topic,
#             "subtopic": subtopic,
#             "timestamp": conversation.timestamp,  # Use conversation timestamp
#             "company_targeting_enabled": manifest_blueprint.get("company_targeting_enabled", False),
#             "key_companies": manifest_blueprint.get("key_companies", []),
#             "company_mention_count": company_mention_count,
#             "company_mentions_by_name": company_mentions_by_name,
#             "companies_found": companies_found,
#             "has_company_mentions": has_company_mentions
#         }
        
#         self.manifest_logger.info(json.dumps(manifest_data))
    
#     def save_conversation_file(self, advisor_name: str, client_name: str, 
#                               conversation_file: ConversationFile):
#         """
#         Save a conversation file to disk.
        
#         Args:
#             advisor_name: Name of the advisor
#             client_name: Name of the client
#             conversation_file: ConversationFile to save
#         """
#         # Create sanitized filename
#         sanitized_advisor = sanitize_filename(advisor_name)
#         sanitized_client = sanitize_filename(client_name)
#         filename = f"{sanitized_advisor}_{sanitized_client}_{uuid.uuid4().hex[:6]}.json"
        
#         file_path = self.output_dir / filename
        
#         with open(file_path, 'w') as f:
#             json.dump(conversation_file.to_dict(), f, indent=2)
        
#         logging.info(f"Saved conversation file: {file_path}")
    
#     def initialize_client_advisor_map(self):
#         """
#         Initialize the client-advisor mapping based on configuration.
#         This creates a dictionary that maps advisors to their clients.
#         """
#         # Check if client-advisor distribution is configured
#         if not hasattr(self.config, 'CLIENT_ADVISOR_DISTRIBUTION') or not self.config.CLIENT_ADVISOR_DISTRIBUTION.get("enabled", False):
#             # No custom distribution, each advisor can have any client
#             self.client_advisor_map = {
#                 advisor: self.config.CLIENT_NAMES.copy() for advisor in self.config.ADVISOR_NAMES
#             }
#             return
            
#         distribution = self.config.CLIENT_ADVISOR_DISTRIBUTION
#         distribution_type = distribution.get("distribution_type", "uniform")
        
#         # Start with empty mapping
#         self.client_advisor_map = {advisor: [] for advisor in self.config.ADVISOR_NAMES}
        
#         # Handle custom pairings if provided
#         custom_pairings = distribution.get("custom_pairings", {})
#         for advisor, clients in custom_pairings.items():
#             if advisor in self.client_advisor_map:
#                 self.client_advisor_map[advisor] = clients.copy()
        
#         # If using custom pairings only, we're done
#         if distribution_type == "custom" and custom_pairings:
#             # Ensure all advisors have at least some clients
#             for advisor, clients in self.client_advisor_map.items():
#                 if not clients:
#                     self.client_advisor_map[advisor] = random.sample(
#                         self.config.CLIENT_NAMES, 
#                         min(3, len(self.config.CLIENT_NAMES))
#                     )
#             return
        
#         # For algorithmic distributions (uniform or weighted)
#         remaining_advisors = [
#             advisor for advisor in self.config.ADVISOR_NAMES 
#             if not self.client_advisor_map[advisor]  # Skip advisors with custom pairings
#         ]
        
#         # Handle special cases
#         special_cases = distribution.get("special_cases", {})
#         low_client_advisors = special_cases.get("low_client_advisors", [])
#         high_client_advisors = special_cases.get("high_client_advisors", [])
        
#         # Remove special case advisors from regular distribution
#         for advisor in low_client_advisors + high_client_advisors:
#             if advisor in remaining_advisors:
#                 remaining_advisors.remove(advisor)
        
#         # Apply distribution based on type
#         if distribution_type == "weighted":
#             # Calculate ratios for Pareto-like distribution
#             high_volume_ratio = distribution.get("high_volume_advisor_ratio", 0.2)
#             high_client_ratio = distribution.get("high_volume_client_ratio", 0.2)
            
#             # Calculate number of high-volume advisors (excluding special cases)
#             num_high_volume = max(1, int(len(remaining_advisors) * high_volume_ratio))
#             high_volume_advisors = random.sample(remaining_advisors, num_high_volume)
#             regular_advisors = [adv for adv in remaining_advisors if adv not in high_volume_advisors]
            
#             # Assign clients to high-volume advisors (large client list)
#             clients_per_high_volume = max(
#                 15,  # Minimum 15 clients (increased from 5)
#                 int((len(self.config.CLIENT_NAMES) * high_client_ratio) / len(high_volume_advisors))
#             )
            
#             # Assign clients to regular advisors (smaller client list)
#             clients_per_regular = max(
#                 8,  # Minimum 8 clients (increased from 1)
#                 int((len(self.config.CLIENT_NAMES) * (1 - high_client_ratio)) / len(regular_advisors))
#             ) if regular_advisors else 0
            
#             # Assign clients
#             for advisor in high_volume_advisors:
#                 self.client_advisor_map[advisor] = random.sample(
#                     self.config.CLIENT_NAMES,
#                     min(clients_per_high_volume, len(self.config.CLIENT_NAMES))
#                 )
                
#             for advisor in regular_advisors:
#                 self.client_advisor_map[advisor] = random.sample(
#                     self.config.CLIENT_NAMES,
#                     min(clients_per_regular, len(self.config.CLIENT_NAMES))
#                 )
                
#         else:  # uniform distribution
#             # Distribute clients evenly
#             clients_per_advisor = max(
#                 15,  # Minimum 15 clients per advisor (increased from 1)
#                 int(len(self.config.CLIENT_NAMES) * 0.7 / len(remaining_advisors))
#             )
            
#             for advisor in remaining_advisors:
#                 self.client_advisor_map[advisor] = random.sample(
#                     self.config.CLIENT_NAMES,
#                     min(clients_per_advisor, len(self.config.CLIENT_NAMES))
#                 )
        
#         # Handle special cases
#         for advisor in low_client_advisors:
#             if advisor in self.client_advisor_map:
#                 # Assign very few clients (1-2)
#                 self.client_advisor_map[advisor] = random.sample(
#                     self.config.CLIENT_NAMES,
#                     min(random.randint(1, 2), len(self.config.CLIENT_NAMES))
#                 )
                
#         for advisor in high_client_advisors:
#             if advisor in self.client_advisor_map:
#                 # Assign many clients (40-60% of all clients)
#                 client_count = int(len(self.config.CLIENT_NAMES) * random.uniform(0.10, 0.20))
#                 self.client_advisor_map[advisor] = random.sample(
#                     self.config.CLIENT_NAMES,
#                     min(client_count, len(self.config.CLIENT_NAMES))
#                 )
        
#         # Ensure every advisor has at least one client
#         for advisor, clients in self.client_advisor_map.items():
#             if not clients:
#                 self.client_advisor_map[advisor] = random.sample(
#                     self.config.CLIENT_NAMES, 
#                     min(1, len(self.config.CLIENT_NAMES))
#                 )
                
#         # Log the distribution
#         client_counts = {advisor: len(clients) for advisor, clients in self.client_advisor_map.items()}
#         logging.info(f"Client-advisor distribution: {client_counts}")
    
#     def select_advisors_clients(self) -> Tuple[str, str]:
#         """
#         Select a random advisor-client pair from available names,
#         respecting the client-advisor distribution if configured.
        
#         Returns:
#             Tuple of (advisor_name, client_name)
#         """
#         # Initialize client-advisor map if not already done
#         if not hasattr(self, 'client_advisor_map'):
#             self.initialize_client_advisor_map()
            
#         # Select a random advisor
#         advisor = random.choice(self.config.ADVISOR_NAMES)
        
#         # Select a client for this advisor based on the mapping
#         if advisor in self.client_advisor_map and self.client_advisor_map[advisor]:
#             client = random.choice(self.client_advisor_map[advisor])
#         else:
#             # Fallback if no clients are assigned to this advisor
#             client = random.choice(self.config.CLIENT_NAMES)
            
#         logging.debug(f"Selected advisor-client pair: {advisor} - {client}")
#         return advisor, client
    
#     def select_conversation_type(self) -> str:
#         """
#         Select a random conversation type from available types.
        
#         Returns:
#             Selected conversation type
#         """
#         conversation_type = random.choice(self.config.CONVERSATION_TYPES)
#         logging.debug(f"Selected conversation type: {conversation_type}")
#         return conversation_type
    
#     def calculate_conversation_count(self):
#         """Calculate conversation count based on config settings."""
#         if not hasattr(self.config, 'DAILY_CONVERSATION_TARGET') or self.config.DAILY_CONVERSATION_TARGET is None:
#             return self.config.NUM_CONVERSATIONS
            
#         if not hasattr(self.config, 'START_DATE') or not hasattr(self.config, 'END_DATE'):
#             logging.warning("DAILY_CONVERSATION_TARGET requires START_DATE and END_DATE. Using NUM_CONVERSATIONS instead.")
#             return self.config.NUM_CONVERSATIONS
            
#         # Calculate days between dates
#         start = datetime.fromisoformat(self.config.START_DATE)
#         end = datetime.fromisoformat(self.config.END_DATE)
#         days = (end - start).days + 1
        
#         # Calculate total conversations based on daily target
#         calculated_count = int(days * self.config.DAILY_CONVERSATION_TARGET)
        
#         # Handle enforcement preference
#         if hasattr(self.config, 'ENFORCE_EXACT_COUNT') and self.config.ENFORCE_EXACT_COUNT:
#             if calculated_count != self.config.NUM_CONVERSATIONS:
#                 logging.warning(f"Calculated count ({calculated_count}) differs from NUM_CONVERSATIONS ({self.config.NUM_CONVERSATIONS})")
#                 logging.warning(f"Using NUM_CONVERSATIONS due to ENFORCE_EXACT_COUNT=True")
#             return self.config.NUM_CONVERSATIONS
#         else:
#             logging.info(f"Using calculated conversation count: {calculated_count} based on {self.config.DAILY_CONVERSATION_TARGET} per day for {days} days")
#             return calculated_count
    
#     async def generate_synthetic_data(self):
#         """
#         Main method to generate synthetic data.
        
#         This orchestrates the entire process of generating multiple conversations
#         according to the configuration.
#         """
#         # Calculate the number of conversations to generate
#         num_conversations = self.calculate_conversation_count()
        
#         logging.info(f"Starting synthetic data generation with run_id: {self.run_id}")
#         logging.info(f"Generating {num_conversations} conversations")
        
#         # Initialize the LLM provider
#         await self.llm_provider.initialize()
        
#         # Precalculate conversation distribution if datetime strategy is available
#         if self.datetime_strategy and hasattr(self.config, 'START_DATE') and hasattr(self.config, 'END_DATE'):
#             time_period = (self.config.START_DATE, self.config.END_DATE)
#             logging.info(f"Generating temporal distribution for time period: {time_period[0]} to {time_period[1]}")
            
#             distribution = self.datetime_strategy.get_message_count_distribution(
#                 time_period, self.config.NUM_CONVERSATIONS
#             )
            
#             # Log the distribution summary by month
#             monthly_summary = {}
#             for date_str, count in distribution.items():
#                 month = date_str[:7]  # Extract YYYY-MM
#                 if month not in monthly_summary:
#                     monthly_summary[month] = 0
#                 monthly_summary[month] += count
                
#             logging.info(f"Conversation distribution by month: {monthly_summary}")
        
#         # Track conversation pairing to group multiple conversations between the same people
#         self.conversation_buffer = {}
        
#         # Log statistics about client-advisor distribution
#         if hasattr(self, 'client_advisor_map'):
#             client_counts = {advisor: len(clients) for advisor, clients in self.client_advisor_map.items()}
#             # Sort advisors by client count for better visualization
#             sorted_counts = sorted(client_counts.items(), key=lambda x: x[1], reverse=True)
            
#             # Calculate summary statistics
#             total_clients = sum(client_counts.values())
#             avg_clients = total_clients / len(client_counts) if client_counts else 0
#             min_clients = min(client_counts.values()) if client_counts else 0
#             max_clients = max(client_counts.values()) if client_counts else 0
            
#             logging.info(f"\n===== CLIENT-ADVISOR DISTRIBUTION =====")
#             logging.info(f"Total unique client-advisor pairings: {total_clients}")
#             logging.info(f"Average clients per advisor: {avg_clients:.2f}")
#             logging.info(f"Range: {min_clients} to {max_clients} clients per advisor")
            
#             # Display distribution
#             logging.info("\n----- Clients per Advisor -----")
#             for advisor, count in sorted_counts:
#                 percentage = (count / len(self.config.CLIENT_NAMES)) * 100
#                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                 logging.info(f"{advisor}: {count} clients ({percentage:.1f}%) {bar}")
        
#         for i in range(1, self.config.NUM_CONVERSATIONS + 1):
#             try:
#                 advisor_name, client_name = self.select_advisors_clients()
#                 conversation_type = self.select_conversation_type()
                
#                 # Determine number of messages for this conversation
#                 num_messages = random.randint(self.config.MIN_MESSAGES, self.config.MAX_MESSAGES)
                
#                 # Generate the conversation
#                 conversation = await self.process_conversation(
#                     conv_number=i,
#                     conversation_type=conversation_type,
#                     advisor_name=advisor_name,
#                     client_name=client_name,
#                     num_messages=num_messages
#                 )
                
#                 if not conversation:
#                     logging.warning(f"Failed to generate conversation {i}, skipping")
#                     continue
                
#                 # Add to conversation buffer (for grouping)
#                 buffer_key = f"{advisor_name}_{client_name}"
#                 if buffer_key not in self.conversation_buffer:
#                     self.conversation_buffer[buffer_key] = ConversationFile(
#                         version=self.config.JSON_VERSION,
#                         advisor=advisor_name,
#                         client=client_name,
#                         conversations=[]
#                     )
                
#                 self.conversation_buffer[buffer_key].conversations.append(conversation)
                
#                 # Save after every few conversations or when buffer gets too large
#                 if i % 5 == 0 or len(self.conversation_buffer[buffer_key].conversations) >= 10:
#                     self.save_conversation_file(
#                         advisor_name, client_name, self.conversation_buffer[buffer_key]
#                     )
#                     # Clear buffer after saving
#                     self.conversation_buffer[buffer_key].conversations = []
                
#                 # Progress update
#                 if i % 10 == 0:
#                     logging.info(f"Generated {i}/{self.config.NUM_CONVERSATIONS} conversations")
                
#             except Exception as e:
#                 logging.error(f"Error generating conversation {i}: {e}", exc_info=True)
        
#         # Save any remaining conversations in the buffer
#         for buffer_key, conversation_file in self.conversation_buffer.items():
#             if conversation_file.conversations:
#                 advisor_name, client_name = buffer_key.split('_', 1)
#                 self.save_conversation_file(advisor_name, client_name, conversation_file)
        
#         # Log summary of client-advisor interactions
#         if hasattr(self, 'advisor_client_interactions') and self.advisor_client_interactions:
#             # Sort by number of interactions
#             sorted_interactions = sorted(
#                 self.advisor_client_interactions.items(), 
#                 key=lambda x: x[1], 
#                 reverse=True
#             )
            
#             # Group by advisor
#             advisor_interaction_counts = {}
#             advisor_unique_clients = {}
#             for pair, count in sorted_interactions:
#                 advisor, client = pair.split('|')
#                 if advisor not in advisor_interaction_counts:
#                     advisor_interaction_counts[advisor] = 0
#                     advisor_unique_clients[advisor] = set()
#                 advisor_interaction_counts[advisor] += count
#                 advisor_unique_clients[advisor].add(client)
            
#             # Log advisor activity summary
#             logging.info("\n===== ADVISOR-CLIENT INTERACTION SUMMARY =====")
#             logging.info(f"Total unique advisor-client pairs with conversations: {len(self.advisor_client_interactions)}")
            
#             # Most active advisors
#             logging.info("\n----- Advisor Activity (by conversation count) -----")
#             # Calculate max count for scaling histogram bars
#             max_advisor_count = max(advisor_interaction_counts.values()) if advisor_interaction_counts else 0
            
#             for advisor, count in sorted(advisor_interaction_counts.items(), key=lambda x: x[1], reverse=True):
#                 unique_count = len(advisor_unique_clients[advisor])
#                 percentage = (count / self.config.NUM_CONVERSATIONS) * 100
#                 # Scale bar length by percentage for consistent visualization
#                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                 logging.info(f"{advisor}: {count} conversations ({percentage:.1f}%), {unique_count} unique clients {bar}")
            
#             # Client distribution (how many advisors each client has)
#             client_advisor_counts = {}
#             for pair in self.advisor_client_interactions:
#                 advisor, client = pair.split('|')
#                 if client not in client_advisor_counts:
#                     client_advisor_counts[client] = set()
#                 client_advisor_counts[client].add(advisor)
            
#             # Convert sets to counts
#             client_advisor_counts = {client: len(advisors) for client, advisors in client_advisor_counts.items()}
            
#             # Group clients by number of advisors
#             advisors_per_client = {}
#             for client, count in client_advisor_counts.items():
#                 if count not in advisors_per_client:
#                     advisors_per_client[count] = 0
#                 advisors_per_client[count] += 1
            
#             # Log client distribution 
#             logging.info("\n----- Client Distribution (by advisor count) -----")
#             for adv_count in sorted(advisors_per_client.keys()):
#                 client_count = advisors_per_client[adv_count]
#                 percentage = (client_count / len(client_advisor_counts)) * 100
#                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                 logging.info(f"Clients with {adv_count} advisors: {client_count} clients ({percentage:.1f}%) {bar}")
            
#             # Visual histogram of advisors by number of clients
#             clients_per_advisor_histogram = {}
#             for advisor, clients in advisor_unique_clients.items():
#                 client_count = len(clients)
#                 if client_count not in clients_per_advisor_histogram:
#                     clients_per_advisor_histogram[client_count] = 0
#                 clients_per_advisor_histogram[client_count] += 1
            
#             logging.info("\n----- Distribution of Advisors by Client Count -----")
#             # Calculate max for scaling histogram
#             max_bin_count = max(clients_per_advisor_histogram.values()) if clients_per_advisor_histogram else 0
            
#             for client_count in sorted(clients_per_advisor_histogram.keys()):
#                 advisor_count = clients_per_advisor_histogram[client_count]
#                 percentage = (advisor_count / len(advisor_unique_clients)) * 100
#                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                 logging.info(f"Advisors with {client_count} clients: {advisor_count} advisors ({percentage:.1f}%) {bar}")
            
#             # Generate heat map of conversation density
#             # Create matrix showing conversation count for each advisor-client pair
#             logging.info("\n----- Conversation Density Heat Map -----")
#             top_advisors = [adv for adv, _ in sorted(advisor_interaction_counts.items(), 
#                                                 key=lambda x: x[1], reverse=True)[:5]]
#             top_clients = []
#             # Find clients who have had conversations with these top advisors
#             for advisor in top_advisors:
#                 for pair in self.advisor_client_interactions:
#                     adv, client = pair.split('|')
#                     if adv == advisor and client not in top_clients:
#                         top_clients.append(client)
#                         if len(top_clients) >= 5:  # Limit to 5 clients for readability
#                             break
            
#             # Generate the heat map header
#             logging.info(f"{'Advisor/Client':<20} | " + " | ".join(f"{client:<15}" for client in top_clients))
#             logging.info("-" * 20 + "-+-" + "-+-".join("-" * 15 for _ in top_clients))
            
#             # Generate heat map rows
#             for advisor in top_advisors:
#                 row = f"{advisor:<20} | "
#                 for client in top_clients:
#                     pair_key = f"{advisor}|{client}"
#                     conv_count = self.advisor_client_interactions.get(pair_key, 0)
#                     # Generate heat indicator
#                     if conv_count == 0:
#                         heat = " " * 15  # Empty for zero
#                     else:
#                         # Scale heat indicators by count
#                         heat_chars = "▁▂▃▄▅▆▇█"  # Ascending heat indicators
#                         max_pair_count = max(self.advisor_client_interactions.values())
#                         heat_idx = min(7, int((conv_count / max_pair_count) * 8)) if max_pair_count > 0 else 0
#                         heat = f"{conv_count} {heat_chars[heat_idx] * 5:<10}"
#                     row += f"{heat:<15} | "
#                 logging.info(row)
            
#             # Top advisor-client pairs
#             logging.info("\n----- Top Advisor-Client Pairs -----")
#             for i, (pair, count) in enumerate(sorted_interactions[:10]):  # Show top 10
#                 advisor, client = pair.split('|')
#                 percentage = (count / self.config.NUM_CONVERSATIONS) * 100
#                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                 logging.info(f"{i+1}. {advisor} - {client}: {count} conversations ({percentage:.1f}%) {bar}")
                
#             # Write detailed interaction data to a file
#             try:
#                 interaction_path = Path(self.config.OUTPUT_DIR) / f"advisor_client_interactions_{self.run_id}.txt"
#                 with open(interaction_path, 'w') as f:
#                     f.write("===== ADVISOR-CLIENT INTERACTIONS =====\n")
#                     f.write(f"Total pairs: {len(self.advisor_client_interactions)}\n\n")
                    
#                     # Write histogram visualization to file
#                     f.write("--- Advisor Activity Histogram ---\n")
#                     # Create ASCII histogram representation
#                     max_name_length = max(len(advisor) for advisor in advisor_interaction_counts.keys())
#                     max_count = max(advisor_interaction_counts.values())
#                     histogram_width = 50  # Width of histogram bars
                    
#                     for advisor, count in sorted(advisor_interaction_counts.items(), key=lambda x: x[1], reverse=True):
#                         unique_count = len(advisor_unique_clients[advisor])
#                         bar_length = int((count / max_count) * histogram_width) if max_count > 0 else 0
#                         bar = '█' * bar_length
#                         percentage = (count / self.config.NUM_CONVERSATIONS) * 100
#                         f.write(f"{advisor:<{max_name_length}} | {bar} {count} ({percentage:.1f}%), {unique_count} clients\n")
                    
#                     # Distribution of advisors by client count
#                     f.write("\n--- Distribution of Advisors by Client Count ---\n")
#                     for client_count in sorted(clients_per_advisor_histogram.keys()):
#                         advisor_count = clients_per_advisor_histogram[client_count]
#                         f.write(f"Advisors with {client_count} clients: {advisor_count}\n")
                    
#                     # Distribution of clients by advisor count
#                     f.write("\n--- Distribution of Clients by Advisor Count ---\n")
#                     for adv_count in sorted(advisors_per_client.keys()):
#                         client_count = advisors_per_client[adv_count]
#                         f.write(f"Clients with {adv_count} advisors: {client_count}\n")
                    
#                     # Complete interaction matrix
#                     f.write("\n--- Complete Interaction Matrix ---\n")
#                     # Create matrix header with all clients
#                     all_clients = sorted(list(set(client for pair in self.advisor_client_interactions.keys() 
#                                                for _, client in [pair.split('|')])))
                    
#                     # Write CSV-style matrix (for potential import into spreadsheet software)
#                     f.write("Advisor," + ",".join(all_clients) + "\n")
                    
#                     for advisor in sorted(advisor_interaction_counts.keys()):
#                         row = [advisor]
#                         for client in all_clients:
#                             pair_key = f"{advisor}|{client}"
#                             conv_count = self.advisor_client_interactions.get(pair_key, 0)
#                             row.append(str(conv_count))
#                         f.write(",".join(row) + "\n")
                    
#                     # By Advisor
#                     f.write("\n--- By Advisor ---\n")
#                     for advisor, count in sorted(advisor_interaction_counts.items(), key=lambda x: x[1], reverse=True):
#                         unique_count = len(advisor_unique_clients[advisor])
#                         f.write(f"{advisor}: {count} conversations, {unique_count} unique clients\n")
#                         # List all clients for this advisor
#                         for client in sorted(advisor_unique_clients[advisor]):
#                             pair_key = f"{advisor}|{client}"
#                             conv_count = self.advisor_client_interactions.get(pair_key, 0)
#                             f.write(f"  - {client}: {conv_count} conversations\n")
                    
#                     # By Client
#                     f.write("\n--- By Client ---\n")
#                     client_conversation_counts = {}
#                     for pair, count in self.advisor_client_interactions.items():
#                         _, client = pair.split('|')
#                         if client not in client_conversation_counts:
#                             client_conversation_counts[client] = 0
#                         client_conversation_counts[client] += count
                    
#                     for client, count in sorted(client_conversation_counts.items(), key=lambda x: x[1], reverse=True):
#                         f.write(f"{client}: {count} total conversations\n")
#                         # List all advisors for this client
#                         for advisor in [adv for adv, cli in [pair.split('|') for pair in self.advisor_client_interactions if client in pair]]:
#                             pair_key = f"{advisor}|{client}"
#                             conv_count = self.advisor_client_interactions.get(pair_key, 0)
#                             if conv_count > 0:
#                                 f.write(f"  - {advisor}: {conv_count} conversations\n")
                        
#                     # By Advisor-Client Pair
#                     f.write("\n--- By Advisor-Client Pair ---\n")
#                     for pair, count in sorted_interactions:
#                         advisor, client = pair.split('|')
#                         f.write(f"{advisor} - {client}: {count}\n")
                        
#                 logging.info(f"\nDetailed advisor-client interaction data written to: {interaction_path}")
#             except Exception as e:
#                 logging.warning(f"Could not write advisor-client interaction file: {e}")
        
#         # Track company mention metrics if company targeting is enabled
#         if hasattr(self, 'manifest_logger') and self.manifest_logger:
#             try:
#                 # Parse each line of the manifest log to count company metrics
#                 from collections import Counter

#                 company_metrics = {
#                     'total_conversations': self.config.NUM_CONVERSATIONS,
#                     'total_conversations_with_companies': 0,
#                     'total_company_mentions': 0,
#                     'company_mention_counts': Counter(),
#                     'company_enabled_count': 0,
#                     'conversations_with_companies': {
#                         '1_company': 0,
#                         '2_companies': 0, 
#                         '3+_companies': 0
#                     }
#                 }
                
#                 manifest_log_file = None
#                 if hasattr(self.config, 'CONVERSATION_MANIFEST_DIR'):
#                     manifest_dir = Path(self.config.CONVERSATION_MANIFEST_DIR)
#                     manifest_log_file = manifest_dir / f"conversation_manifest_{self.run_id}.log"
                
#                 if manifest_log_file and manifest_log_file.exists():
#                     with open(manifest_log_file, 'r') as f:
#                         for line in f:
#                             try:
#                                 data = json.loads(line.strip())
                                
#                                 # Count conversations with targeting enabled
#                                 if data.get('company_targeting_enabled'):
#                                     company_metrics['company_enabled_count'] += 1
                                    
#                                     # For targeted conversations, check if companies actually appear in text
#                                     # Check the companies_found field which contains detected companies 
#                                     companies_found = data.get('companies_found', [])
#                                     is_targeted_conversation = data.get('company_targeting_enabled', False)
                                    
#                                     # Only count company metrics for conversations where targeting was enabled
#                                     if is_targeted_conversation:
#                                         if companies_found:
#                                             company_metrics['total_conversations_with_companies'] += 1
                                            
#                                             # Track distribution of company counts
#                                             num_companies = len(companies_found)
#                                             if num_companies == 1:
#                                                 company_metrics['conversations_with_companies']['1_company'] += 1
#                                             elif num_companies == 2:
#                                                 company_metrics['conversations_with_companies']['2_companies'] += 1
#                                             elif num_companies >= 3:
#                                                 company_metrics['conversations_with_companies']['3+_companies'] += 1
                                    
#                                             # Track counts by company name from the companies_found list
#                                             for company in companies_found:
#                                                 company_metrics['company_mention_counts'][company] += 1
#                                                 company_metrics['total_company_mentions'] += 1
#                             except json.JSONDecodeError:
#                                 continue
                    
#                     # Log company mention metrics if any data was collected
#                     if company_metrics['company_enabled_count'] > 0:
#                         logging.info("\n===== COMPANY TARGETING METRICS =====")
                        
#                         # Configuration summary
#                         probability = self.generation_strategy.company_targeting.get("probability", 0.4) if hasattr(self.generation_strategy, 'company_targeting') else 0.4
#                         logging.info(f"Company targeting configuration: probability={probability:.2f}, "
#                                      f"min_companies={self.generation_strategy.company_targeting.get('min_companies', 1)}, "
#                                      f"max_companies={self.generation_strategy.company_targeting.get('max_companies', 3)}")
                        
#                         # Base metrics
#                         enabled_pct = (company_metrics['company_enabled_count'] / company_metrics['total_conversations'] * 100)
#                         logging.info(f"Conversations with company targeting enabled: {company_metrics['company_enabled_count']} " + 
#                                     f"({enabled_pct:.1f}% of all conversations)")
                        
#                         # Expected number of conversations with company targeting
#                         expected_count = int(company_metrics['total_conversations'] * probability)
#                         logging.info(f"Expected conversations with company targeting: {expected_count} " + 
#                                     f"({probability*100:.1f}% of all conversations)")
                        
#                         # Conversations with company mentions
#                         success_pct = (company_metrics['total_conversations_with_companies'] / company_metrics['company_enabled_count'] * 100) if company_metrics['company_enabled_count'] > 0 else 0
#                         overall_pct = (company_metrics['total_conversations_with_companies'] / company_metrics['total_conversations'] * 100)
                        
#                         logging.info(f"Conversations with at least one company mentioned: {company_metrics['total_conversations_with_companies']} " + 
#                                    f"({success_pct:.1f}% success rate, {overall_pct:.1f}% of all conversations)")
                        
#                         # Distribution of number of companies per conversation
#                         logging.info("\n----- Company Count Distribution -----")
#                         for company_count, count in company_metrics['conversations_with_companies'].items():
#                             if company_metrics['total_conversations_with_companies'] > 0:
#                                 percentage = (count / company_metrics['total_conversations_with_companies']) * 100
#                                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                                 logging.info(f"{company_count}: {count} conversations ({percentage:.1f}%) {bar}")
                        
#                         # Average metrics
#                         if company_metrics['total_conversations_with_companies'] > 0:
#                             avg_mentions = company_metrics['total_company_mentions'] / company_metrics['total_conversations_with_companies']
#                             logging.info(f"\nAverage company mentions per conversation (when present): {avg_mentions:.2f}")
                            
#                             # Count distribution of number of mentions
#                             mention_counts = Counter()
#                             for line in open(manifest_log_file, 'r'):
#                                 try:
#                                     data = json.loads(line.strip())
#                                     if data.get('has_company_mentions', False):
#                                         count = data.get('company_mention_count', 0)
#                                         mention_counts[count] += 1
#                                 except json.JSONDecodeError:
#                                     continue
                            
#                             # Display distribution of mentions per conversation
#                             if mention_counts:
#                                 logging.info("\n----- Company Mentions Distribution -----")
#                                 for count in sorted(mention_counts.keys()):
#                                     frequency = mention_counts[count]
#                                     pct = (frequency / company_metrics['total_conversations_with_companies']) * 100 if company_metrics['total_conversations_with_companies'] > 0 else 0
#                                     bar = "█" * int(pct / 5)  # Visual bar (each █ = 5%)
#                                     logging.info(f"{count} mentions: {frequency} conversations ({pct:.1f}%) {bar}")
                        
#                         # Display top mentioned companies
#                         top_companies = company_metrics['company_mention_counts'].most_common(10)
#                         if top_companies:
#                             logging.info("\n----- Top 10 Company Mentions -----")
#                             max_count = top_companies[0][1] if top_companies else 0
#                             for company, count in top_companies:
#                                 percentage = (count / company_metrics['total_company_mentions']) * 100 if company_metrics['total_company_mentions'] > 0 else 0
#                                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                                 logging.info(f"{company}: {count} mentions ({percentage:.1f}%) {bar}")
                                
#                         # Log success rate of finding companies when enabled
#                         not_found = company_metrics['company_enabled_count'] - company_metrics['total_conversations_with_companies']
#                         if not_found > 0:
#                             not_found_pct = (not_found / company_metrics['company_enabled_count']) * 100
#                             logging.warning(f"\nTarget companies not found in {not_found} conversations ({not_found_pct:.1f}% miss rate)")
#                             if not_found_pct > 20:  # Only show warning if miss rate is high
#                                 logging.warning(f"High miss rate may indicate prompt engineering issues or LLM compliance problems")
#             except Exception as e:
#                 logging.warning(f"Error processing company metrics: {e}")
                
#         # Log summary of temporal distribution
#         if hasattr(self, 'all_timestamps') and self.all_timestamps:
#             # Group by date
#             date_counts = {}
#             for ts in self.all_timestamps:
#                 date_str = datetime.fromisoformat(ts).date().isoformat()
#                 if date_str not in date_counts:
#                     date_counts[date_str] = 0
#                 date_counts[date_str] += 1
                
#             # Group by month
#             month_counts = {}
#             for ts in self.all_timestamps:
#                 dt = datetime.fromisoformat(ts)
#                 month_str = dt.strftime('%Y-%m')  # Format: YYYY-MM
#                 if month_str not in month_counts:
#                     month_counts[month_str] = 0
#                 month_counts[month_str] += 1
            
#             # Group by week
#             week_counts = {}
#             for ts in self.all_timestamps:
#                 dt = datetime.fromisoformat(ts)
#                 week_num = dt.isocalendar()[1]  # ISO week number
#                 week_str = f"{dt.year}-W{week_num:02d}"
#                 if week_str not in week_counts:
#                     week_counts[week_str] = 0
#                 week_counts[week_str] += 1
            
#             # Group by day of week
#             day_counts = {'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 
#                          'Thursday': 0, 'Friday': 0, 'Saturday': 0, 'Sunday': 0}
#             weekday_by_month = {}  # Track weekday distribution by month
#             for ts in self.all_timestamps:
#                 dt = datetime.fromisoformat(ts)
#                 day_name = dt.strftime('%A')
#                 day_counts[day_name] += 1
                
#                 # Track weekday by month
#                 month_str = dt.strftime('%Y-%m')
#                 if month_str not in weekday_by_month:
#                     weekday_by_month[month_str] = {day: 0 for day in day_counts.keys()}
#                 weekday_by_month[month_str][day_name] += 1
                
#             # Group by hour
#             hour_counts = {h: 0 for h in range(24)}
#             for ts in self.all_timestamps:
#                 hour = datetime.fromisoformat(ts).hour
#                 hour_counts[hour] += 1
            
#             # Calculate date range and total days
#             sorted_dates = sorted(date_counts.items())
#             first_date = datetime.fromisoformat(sorted_dates[0][0] + "T00:00:00").date()
#             last_date = datetime.fromisoformat(sorted_dates[-1][0] + "T00:00:00").date()
#             total_days = (last_date - first_date).days + 1
            
#             # Calculate days with conversations
#             days_with_conversations = len(date_counts)
#             coverage_percentage = (days_with_conversations / total_days) * 100 if total_days > 0 else 0
            
#             # Log the distributions
#             logging.info("\n===== TEMPORAL DISTRIBUTION SUMMARY =====")
#             logging.info(f"Total conversations generated: {len(self.all_timestamps)}")
#             logging.info(f"Date range: from {sorted_dates[0][0]} to {sorted_dates[-1][0]} ({total_days} days)")
#             logging.info(f"Days with conversations: {days_with_conversations} ({coverage_percentage:.1f}% coverage)")
            
#             # Log monthly distribution
#             logging.info("\n----- Monthly Distribution -----")
#             for month, count in sorted(month_counts.items()):
#                 percentage = (count / len(self.all_timestamps)) * 100
#                 bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
#                 logging.info(f"{month}: {count} conversations ({percentage:.1f}%) {bar}")
            
#             # Log weekly distribution
#             logging.info("\n----- Weekly Distribution -----")
#             for week, count in sorted(week_counts.items()):
#                 percentage = (count / len(self.all_timestamps)) * 100
#                 bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
#                 logging.info(f"{week}: {count} conversations ({percentage:.1f}%) {bar}")
            
#             # Log day of week distribution
#             logging.info("\n----- Day of Week Distribution -----")
#             for day, count in day_counts.items():
#                 percentage = (count / len(self.all_timestamps)) * 100
#                 bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
#                 logging.info(f"{day}: {count} conversations ({percentage:.1f}%) {bar}")
            
#             # Log day of week by month (if multiple months)
#             if len(month_counts) > 1:
#                 logging.info("\n----- Day of Week Distribution by Month -----")
#                 for month, days in sorted(weekday_by_month.items()):
#                     logging.info(f"\nMonth: {month}")
#                     month_total = sum(days.values())
#                     for day, count in days.items():
#                         percentage = (count / month_total) * 100 if month_total > 0 else 0
#                         bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
#                         logging.info(f"  {day}: {count} conversations ({percentage:.1f}%) {bar}")
            
#             # Format hour distribution with visual bar
#             logging.info("\n----- Hour Distribution -----")
#             max_hour_count = max(hour_counts.values()) if hour_counts else 0
#             for hour in sorted(hour_counts.keys()):
#                 count = hour_counts[hour]
#                 if count > 0:
#                     percentage = (count / len(self.all_timestamps)) * 100
#                     bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
#                     hour_str = f"{hour:02d}:00"
#                     logging.info(f"{hour_str}: {count} conversations ({percentage:.1f}%) {bar}")
            
#             # Generate date-based histogram for longer periods
#             if total_days > 10 and total_days <= 90:  # For medium-length periods (up to 3 months)
#                 logging.info("\n----- Daily Distribution Histogram -----")
#                 # Create a continuous date range
#                 current_date = first_date
#                 while current_date <= last_date:
#                     date_str = current_date.isoformat()
#                     count = date_counts.get(date_str, 0)
#                     day_name = current_date.strftime('%a')  # Abbreviated day name
                    
#                     # Calculate visual representation
#                     if len(self.all_timestamps) > 0:
#                         max_count = max(date_counts.values())
#                         bar_length = min(20, max(1, int((count / max_count) * 20))) if max_count > 0 else 0
#                         bar = "█" * bar_length
#                     else:
#                         bar = ""
                        
#                     logging.info(f"{date_str} ({day_name}): {count:2d} {bar}")
#                     current_date += timedelta(days=1)
            
#             # For very long periods, generate a condensed view by week
#             elif total_days > 90:
#                 logging.info("\n----- Weekly Distribution Histogram -----")
#                 # Group dates by week for visualization
#                 week_of_year = {}
#                 for date_str, count in date_counts.items():
#                     dt = datetime.fromisoformat(date_str + "T00:00:00")
#                     year, week_num, _ = dt.isocalendar()
#                     week_key = f"{year}-W{week_num:02d}"
                    
#                     if week_key not in week_of_year:
#                         week_of_year[week_key] = {
#                             'count': 0,
#                             'start_date': None,
#                             'end_date': None
#                         }
                    
#                     week_of_year[week_key]['count'] += count
                    
#                     # Track start and end dates of the week
#                     if week_of_year[week_key]['start_date'] is None or dt.date() < week_of_year[week_key]['start_date']:
#                         week_of_year[week_key]['start_date'] = dt.date()
                    
#                     if week_of_year[week_key]['end_date'] is None or dt.date() > week_of_year[week_key]['end_date']:
#                         week_of_year[week_key]['end_date'] = dt.date()
                
#                 # Display histogram
#                 max_week_count = max([w['count'] for w in week_of_year.values()]) if week_of_year else 0
                
#                 for week_key, data in sorted(week_of_year.items()):
#                     count = data['count']
#                     start_date = data['start_date'].isoformat() if data['start_date'] else "Unknown"
#                     end_date = data['end_date'].isoformat() if data['end_date'] else "Unknown"
                    
#                     # Calculate visual representation
#                     bar_length = min(20, max(1, int((count / max_week_count) * 20))) if max_week_count > 0 else 0
#                     bar = "█" * bar_length
                    
#                     logging.info(f"{week_key} ({start_date} to {end_date}): {count:3d} conversations {bar}")
            
#             # Show day-by-day summary if we have a very small number of days
#             elif total_days <= 10:
#                 logging.info("\n----- Daily Distribution -----")
#                 for date_str, count in sorted_dates:
#                     day_name = datetime.fromisoformat(date_str + "T00:00:00").strftime('%A')
#                     percentage = (count / len(self.all_timestamps)) * 100
#                     bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
#                     logging.info(f"{date_str} ({day_name}): {count} conversations ({percentage:.1f}%) {bar}")
            
#             # Write summary to a separate file for easier analysis
#             try:
#                 summary_path = Path(self.config.OUTPUT_DIR) / f"temporal_summary_{self.run_id}.txt"
#                 with open(summary_path, 'w') as f:
#                     f.write("===== TEMPORAL DISTRIBUTION SUMMARY =====\n")
#                     f.write(f"Total conversations: {len(self.all_timestamps)}\n")
#                     f.write(f"Date range: {sorted_dates[0][0]} to {sorted_dates[-1][0]} ({total_days} days)\n\n")
                    
#                     f.write("--- Daily Distribution ---\n")
#                     for date_str, count in sorted_dates:
#                         f.write(f"{date_str}: {count}\n")
                        
#                 logging.info(f"\nDetailed temporal distribution summary written to: {summary_path}")
#             except Exception as e:
#                 logging.warning(f"Could not write temporal summary file: {e}")
        
#         logging.info(f"Completed synthetic data generation. Generated {self.config.NUM_CONVERSATIONS} conversations.")


"""
Main generator class for Chat Factory.
"""

import logging
import json
import uuid
import random
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter # Added for metrics
import time
# Assuming these imports exist and are correct
from .models.conversation import ConversationFile, SingleConversation, ChatLine
from .strategies.base import TaxonomyStrategy, GenerationStrategy, FewShotExampleStrategy
from .strategies.base.datetime_strategy import DatetimeStrategy
from .llm.base import LLMProvider
from .config.base_config import BaseConfig
from .utils import ensure_directory, sanitize_filename, SummaryStatisticsLogger



class SyntheticChatGenerator:
    """
    Main generator class that orchestrates the synthetic conversation generation process,
    optimized for concurrent API calls using asyncio.
    """

    def __init__(self,
                 config: BaseConfig,
                 taxonomy_strategy: TaxonomyStrategy,
                 generation_strategy: GenerationStrategy,
                 few_shot_strategy: FewShotExampleStrategy,
                 llm_provider: LLMProvider,
                 datetime_strategy: Optional[DatetimeStrategy] = None):
        """
        Initialize the generator with strategies and config.

        Args:
            config: Configuration settings (should include MAX_CONCURRENT_REQUESTS)
            taxonomy_strategy: Strategy for taxonomy processing
            generation_strategy: Strategy for conversation generation
            few_shot_strategy: Strategy for few-shot examples
            llm_provider: Provider for LLM integration (must be async)
            datetime_strategy: Optional strategy for temporal distribution
        """
        self.config = config
        self.taxonomy_strategy = taxonomy_strategy
        self.generation_strategy = generation_strategy
        self.few_shot_strategy = few_shot_strategy
        self.llm_provider = llm_provider
        self.datetime_strategy = datetime_strategy

        # --- Concurrency Setting ---
        # Get from config or set a default
        self.max_concurrent_requests = getattr(config, 'MAX_CONCURRENT_REQUESTS', 20)
        logging.info(f"Using MAX_CONCURRENT_REQUESTS: {self.max_concurrent_requests}")
        # -------------------------

        # Generate or use run_id
        self.run_id = config.RUN_ID or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        logging.info(f"Using run_id: {self.run_id}")

        # Initialize resources
        self.taxonomy = self.taxonomy_strategy.load_taxonomy(config.TAXONOMY_FILE)
        self.flattened_topics = self.taxonomy_strategy.flatten_taxonomy(self.taxonomy.raw_data)

        # --- Changed: Conversation buffer now holds ConversationFile objects directly ---
        self.conversation_files_buffer: Dict[str, ConversationFile] = {}
        # --- Changed: Track completed conversations count ---
        self.completed_conversations = 0
        self.failed_conversations = 0

        # Setup output directories
        self.output_dir = self.setup_output_directory()

        # Initialize client-advisor distribution
        self.initialize_client_advisor_map()

        # Initialize conversation manifest logger
        try:
            self.manifest_logger = self.setup_manifest_logger()
        except Exception as e:
            logging.warning(f"Could not set up manifest logger: {e}. Conversation manifests will not be saved.")
            self.manifest_logger = None

        # Track all timestamps for distribution analysis
        self.all_timestamps = [] # Note: Appending here is safe in asyncio

        # Track client-advisor interaction counts (initialize earlier)
        self.advisor_client_interactions: Dict[str, int] = {}


    def setup_output_directory(self) -> Path:
        """Set up the output directory."""
        output_dir = Path(self.config.OUTPUT_DIR) / self.run_id
        ensure_directory(str(output_dir))
        logging.info(f"Created output directory: {output_dir}")
        return output_dir

    def setup_manifest_logger(self) -> logging.Logger:
        """Set up a logger for conversation manifests."""
        manifest_dir = Path(self.config.CONVERSATION_MANIFEST_DIR)

        try:
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_logger = logging.getLogger("conversation_manifest")
            manifest_logger.setLevel(logging.INFO)

            for handler in manifest_logger.handlers[:]:
                manifest_logger.removeHandler(handler)
                if hasattr(handler, 'close'):
                    handler.close()

            manifest_log_file = manifest_dir / f"conversation_manifest_{self.run_id}.log"
            handler = logging.FileHandler(manifest_log_file)
            handler.setFormatter(logging.Formatter('%(message)s'))
            manifest_logger.addHandler(handler)
            return manifest_logger
        except (PermissionError, OSError) as e:
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "chat_factory_manifests"
            temp_dir.mkdir(parents=True, exist_ok=True)
            manifest_logger = logging.getLogger("conversation_manifest")
            manifest_logger.setLevel(logging.INFO)

            for handler in manifest_logger.handlers[:]:
                 manifest_logger.removeHandler(handler)
                 if hasattr(handler, 'close'):
                    handler.close()

            manifest_log_file = temp_dir / f"conversation_manifest_{self.run_id}.log"
            handler = logging.FileHandler(manifest_log_file)
            handler.setFormatter(logging.Formatter('%(message)s'))
            manifest_logger.addHandler(handler)
            logging.warning(f"Using temporary directory for manifest logs: {temp_dir} due to error: {e}")
            return manifest_logger

    # --- This method remains largely the same, but ensure LLMProvider is async ---
    async def process_conversation(self, conv_index: int, # Changed name from conv_number for clarity
                                   conversation_type: str,
                                   advisor_name: str, client_name: str,
                                   num_messages: int) -> Optional[Tuple[str, str, SingleConversation]]:
        """
        Process a single conversation. Returns (advisor, client, conversation) or None on failure.

        Args:
            conv_index: Index number for this conversation generation attempt.
            conversation_type: Type of conversation to generate.
            advisor_name: Name of the advisor.
            client_name: Name of the client.
            num_messages: Number of messages to generate.

        Returns:
            A tuple (advisor_name, client_name, SingleConversation) on success, None on failure.
        """
        #start_time = asyncio.get_event_loop().time()
        t0 = time.monotonic() # Overall start time for this specific call
        timing_logs = {}
        try:
            # --- Step 1: Topic Selection ---
            t1 = time.monotonic()
            category, topic, subtopic = self.taxonomy_strategy.select_topic(self.flattened_topics)
            timing_logs["1_select_topic"] = time.monotonic() - t1

            # --- Step 2: Manifest Blueprint ---
            t1 = time.monotonic()
            manifest_blueprint = self.generation_strategy.create_manifest_blueprint(
                conversation_type, (category, topic, subtopic), num_messages
            )
            timing_logs["2_create_manifest"] = time.monotonic() - t1

            # --- Step 3: Few-Shot Examples ---
            t1 = time.monotonic()
            # few_shot_examples = await self.few_shot_strategy.get_examples(
            #     conversation_type, category, topic, subtopic
            # )
            few_shot_examples = ""
            timing_logs["3_get_examples"] = time.monotonic() - t1


            # --- Step 4: Construct Prompt ---
            t1 = time.monotonic()
            prompt = await self.generation_strategy.construct_prompt(
                advisor_name, client_name, conversation_type,
                num_messages, manifest_blueprint, few_shot_examples
            )
            timing_logs["4_construct_prompt"] = time.monotonic() - t1


            # --- Step 5: LLM API Call ---
            t1 = time.monotonic()
            # *** CRITICAL: self.llm_provider.retry_with_backoff MUST be truly async ***
            llm_response = await self.llm_provider.retry_with_backoff(prompt)
            timing_logs["5_llm_api_call"] = time.monotonic() - t1 # Includes potential retries/backoff


            if not llm_response:
                # Log timing even on failure before returning
                total_duration = time.monotonic() - t0
                logging.error(f"Failed LLM call for index {conv_index}. Timings (s): {timing_logs}. Total: {total_duration:.3f}s")
                return None # Indicate failure

            # --- Step 6: Process LLM Response ---
            t1 = time.monotonic()
            conversation_lines = self.generation_strategy.process_llm_response(llm_response)
            if not conversation_lines: # Add check for empty/invalid response processing
                total_duration = time.monotonic() - t0
                logging.error(f"Failed processing LLM response for index {conv_index}. Timings (s): {timing_logs}. Total: {total_duration:.3f}s")
                return None

            # --- Step 7: Timestamps & Object Creation ---
            t1 = time.monotonic()
            # Create conversation object
            formatted_topic = f"{topic}.{subtopic}" if subtopic else topic
            # Use a UUID based on the attempt index and run_id for uniqueness
            conversation_id = f"{self.run_id}_{conv_index}_{uuid.uuid4().hex[:8]}"

            # Generate conversation timestamp using datetime strategy if available
            if self.datetime_strategy:
                # Pass the *overall completed count* if the strategy needs it for sequencing
                # Or pass conv_index if it's just for uniqueness/distribution mapping
                # Let's assume conv_index is sufficient for mapping within the distribution
                conversation_timestamp = self.datetime_strategy.generate_conversation_timestamp(conv_index)
            else:
                conversation_timestamp = datetime.now().isoformat()

            # Track timestamp for distribution analysis (append is safe)
            self.all_timestamps.append(conversation_timestamp)

            # Create basic chat lines
            try:
                chat_lines = [ChatLine(**line) for line in conversation_lines]
            except Exception as e:
                total_duration = time.monotonic() - t0
                logging.error(f"Error creating ChatLine objects for index {conv_index}: {e}. Lines: {conversation_lines}")
                return None # Indicate failure

            # Apply message timestamps if datetime strategy is available
            if self.datetime_strategy:
                try:
                    message_timestamps = self.datetime_strategy.generate_message_timestamps(
                        conversation_timestamp, len(chat_lines)
                    )
                    chat_lines = self.datetime_strategy.apply_timestamps_to_conversation(
                        chat_lines, message_timestamps
                    )
                except Exception as e:
                     logging.warning(f"Error applying message timestamps for {conversation_id}: {e}. Proceeding without message timestamps.")
            timing_logs["7_timestamps_objects"] = time.monotonic() - t1

            # --- Step 8: Company Mentions ---
            t1 = time.monotonic()
            # Analyze company mentions
            company_mentions = []
            if hasattr(self.generation_strategy, 'check_company_mentions') and hasattr(self.generation_strategy, 'company_targeting'):
                if manifest_blueprint.get("company_targeting_enabled", False):
                    company_mentions = manifest_blueprint.get("key_companies", [])
                    formatted_lines = [{"speaker": line.speaker, "text": line.text} for line in chat_lines]
                    mention_results = self.generation_strategy.check_company_mentions(formatted_lines)

                    company_tag = f"[COMPANY METRICS][{conversation_id}]"
                    if mention_results["has_company_mentions"]:
                        logging.debug(f"{company_tag} Found {mention_results['total_mentions']} mentions of {len(mention_results['companies_found'])} companies: {', '.join(mention_results['companies_found'])}")
                        company_mentions = mention_results["companies_found"] # Use actual found companies
                    else:
                        logging.debug(f"{company_tag} No company mentions found despite targeting: {', '.join(company_mentions)}")
                # else: # Optional: Log non-targeted convos
                #    logging.debug(f"[COMPANY METRICS][{conversation_id}] Company targeting disabled.")
            timing_logs["8_check_mentions"] = time.monotonic() - t1

            # --- Step 9: Final Object Creation ---
            t1 = time.monotonic()
            conversation = SingleConversation(
                conversation_id=conversation_id,
                timestamp=conversation_timestamp,
                category=category,
                topic=formatted_topic,
                lines=chat_lines,
                company_mentions=company_mentions
            )
            timing_logs["9_final_object"] = time.monotonic() - t1

            # Log manifest information
            # Note: This might slightly delay the return, but keeps related info together.
            # If this becomes a bottleneck, it could be scheduled separately.
            # --- Step 10: Log Manifest ---
            t1 = time.monotonic()
            self.log_conversation_manifest(
                conv_index, conversation_id, advisor_name, client_name,
                category, topic, subtopic, manifest_blueprint, conversation
            )
            timing_logs["10_log_manifest"] = time.monotonic() - t1

            # Basic timing log
            # end_time = asyncio.get_event_loop().time()
            # duration = end_time - start_time
            # --- Log final timings for this conversation ---
            total_duration = time.monotonic() - t0
            # logging.debug(f"Processed conversation {conversation_id} in {duration:.2f} seconds.")
            # Use DEBUG level to avoid cluttering INFO logs unless specifically debugging performance
            logging.debug(f"Conv {conversation_id} Timing Breakdown (s): { {k: f'{v:.3f}' for k, v in timing_logs.items()} }. Total: {total_duration:.3f}s")


            # --- MODIFIED INFO LOG ---
            # Get the specific timings, default to None if not found (shouldn't happen on success)
            api_time = timing_logs.get('5_llm_api_call')
            proc_time = timing_logs.get('6_process_response')
            # Format them, handle potential None case gracefully
            api_time_str = f"{api_time:.3f}s" if api_time is not None else "N/A"
            proc_time_str = f"{proc_time:.3f}s" if proc_time is not None else "N/A"

            # Add timings to the main INFO log for the conversation
            conv_date = datetime.fromisoformat(conversation.timestamp)
            logging.info(f"✓ Conv {conversation_id} | API: {api_time_str} | Proc: {proc_time_str} | Msgs: {len(conversation.lines)} | Date: {conv_date.strftime('%Y-%m-%d %H:%M:%S')}")
            # --- END MODIFIED INFO LOG ---
            # Return the key info needed to buffer and save
            return advisor_name, client_name, conversation

        except Exception as e:
            # Catch unexpected errors during processing
            # logging.error(f"Unexpected error processing conversation index {conv_index} ({advisor_name}-{client_name}): {e}", exc_info=True)
            total_duration = time.monotonic() - t0
            logging.error(f"Unexpected error processing index {conv_index}. Timings (s): {timing_logs}. Total: {total_duration:.3f}s. Error: {e}", exc_info=True)
            return None # Indicate failure


    def log_conversation_manifest(self, conv_index: int, conversation_id: str,
                                  advisor_name: str, client_name: str,
                                  category: str, topic: str, subtopic: Optional[str],
                                  manifest_blueprint: Dict[str, Any],
                                  conversation: SingleConversation):
        """Log conversation manifest information."""
        if self.manifest_logger is None:
            return

        # --- Moved interaction tracking here for atomicity after conversation success ---
        # Track client-advisor pairing for analytics
        pair_key = f"{advisor_name}|{client_name}"
        # This is safe in asyncio (single thread) but would need a lock in multithreading
        self.advisor_client_interactions[pair_key] = self.advisor_client_interactions.get(pair_key, 0) + 1
        # ---

        # Company mention data
        company_mention_count = 0
        company_mentions_by_name = {}
        companies_found = []
        has_company_mentions = False

        if manifest_blueprint.get("company_targeting_enabled", False):
             if hasattr(conversation, 'company_mentions') and conversation.company_mentions:
                 companies_found = conversation.company_mentions
                 has_company_mentions = True
                 # Count mentions based on the 'companies_found' list from the conversation object
                 mention_counter = Counter(companies_found)
                 company_mentions_by_name = dict(mention_counter)
                 company_mention_count = sum(mention_counter.values()) # Total mentions might differ if a company is mentioned multiple times

        manifest_data = {
            "conversation_id": conversation_id,
            "conv_index": conv_index, # Use the attempt index
            "advisor": advisor_name,
            "client": client_name,
            "category": category,
            "topic": topic,
            "subtopic": subtopic,
            "timestamp": conversation.timestamp,
            "num_messages_actual": len(conversation.lines),
            "num_messages_requested": manifest_blueprint.get("num_messages", "N/A"), # Add requested
            "company_targeting_enabled": manifest_blueprint.get("company_targeting_enabled", False),
            "key_companies_targeted": manifest_blueprint.get("key_companies", []), # Targeted
            "company_mentions_found_count": company_mention_count, # Actual count
            "company_mentions_by_name": company_mentions_by_name, # Actual count by name
            "companies_found": companies_found, # List of unique companies found
            "has_company_mentions": has_company_mentions # Boolean if any found
        }

        self.manifest_logger.info(json.dumps(manifest_data))

    # --- Changed: save_conversation_files_from_buffer ---
    def save_conversation_files_from_buffer(self, force_save_all: bool = False):
        """
        Saves conversation files from the buffer to disk.

        Args:
            force_save_all: If True, saves all files regardless of conversation count.
                            If False, saves only files meeting the buffer threshold.
        """
        logging.debug(f"Checking buffer. {len(self.conversation_files_buffer)} advisor-client pairs buffered.")
        keys_to_clear = []
        save_threshold = self.config.SAVE_BUFFER_THRESHOLD if hasattr(self.config, 'SAVE_BUFFER_THRESHOLD') else 10 # Configurable threshold

        for buffer_key, conversation_file in self.conversation_files_buffer.items():
            should_save = force_save_all or len(conversation_file.conversations) >= save_threshold

            if should_save and conversation_file.conversations:
                advisor_name = conversation_file.advisor
                client_name = conversation_file.client

                # Create sanitized filename (unique name per save operation)
                sanitized_advisor = sanitize_filename(advisor_name)
                sanitized_client = sanitize_filename(client_name)
                # Include timestamp and part number if saving frequently
                timestamp_part = datetime.now().strftime('%H%M%S%f')
                filename = f"{sanitized_advisor}_{sanitized_client}_{timestamp_part}_{uuid.uuid4().hex[:6]}.json"
                file_path = self.output_dir / filename

                try:
                    with open(file_path, 'w') as f:
                        json.dump(conversation_file.to_dict(), f, indent=2)
                    logging.debug(f"Saved {len(conversation_file.conversations)} conversations to: {file_path}")

                    # Mark this buffer key for clearing *after* successful save
                    keys_to_clear.append(buffer_key)

                except IOError as e:
                    logging.error(f"Failed to save conversation file {file_path}: {e}")
                except Exception as e:
                     logging.error(f"Unexpected error saving file {file_path}: {e}", exc_info=True)


        # Clear buffers that were successfully saved
        for key in keys_to_clear:
            # Re-initialize the buffer entry for this pair
             advisor, client = key.split('_', 1) # Assuming key format advisor_client
             self.conversation_files_buffer[key] = ConversationFile(
                 version=self.config.JSON_VERSION,
                 advisor=advisor,
                 client=client,
                 conversations=[]
             )
             logging.debug(f"Cleared buffer for {key} after saving.")


    def initialize_client_advisor_map(self):
        """Initialize the client-advisor mapping (Unchanged - seems okay)."""
        # ... (Keep existing logic) ...
        if not hasattr(self.config, 'CLIENT_ADVISOR_DISTRIBUTION') or not self.config.CLIENT_ADVISOR_DISTRIBUTION.get("enabled", False):
             self.client_advisor_map = {
                 advisor: self.config.CLIENT_NAMES.copy() for advisor in self.config.ADVISOR_NAMES
             }
             logging.info("Initialized uniform client-advisor map (all clients possible for all advisors).")
             return

        # ... (rest of your existing logic for distribution) ...
           
        distribution = self.config.CLIENT_ADVISOR_DISTRIBUTION
        distribution_type = distribution.get("distribution_type", "uniform")
        
        # Start with empty mapping
        self.client_advisor_map = {advisor: [] for advisor in self.config.ADVISOR_NAMES}
        
        # Handle custom pairings if provided
        custom_pairings = distribution.get("custom_pairings", {})
        for advisor, clients in custom_pairings.items():
            if advisor in self.client_advisor_map:
                self.client_advisor_map[advisor] = clients.copy()
        
        # If using custom pairings only, we're done
        if distribution_type == "custom" and custom_pairings:
            # Ensure all advisors have at least some clients
            for advisor, clients in self.client_advisor_map.items():
                if not clients:
                    self.client_advisor_map[advisor] = random.sample(
                        self.config.CLIENT_NAMES, 
                        min(3, len(self.config.CLIENT_NAMES))
                    )
            return
        
        # For algorithmic distributions (uniform or weighted)
        remaining_advisors = [
            advisor for advisor in self.config.ADVISOR_NAMES 
            if not self.client_advisor_map[advisor]  # Skip advisors with custom pairings
        ]
        
        # Handle special cases
        special_cases = distribution.get("special_cases", {})
        low_client_advisors = special_cases.get("low_client_advisors", [])
        high_client_advisors = special_cases.get("high_client_advisors", [])
        
        # Remove special case advisors from regular distribution
        for advisor in low_client_advisors + high_client_advisors:
            if advisor in remaining_advisors:
                remaining_advisors.remove(advisor)
        
        # Apply distribution based on type
        if distribution_type == "weighted":
            # Calculate ratios for Pareto-like distribution
            high_volume_ratio = distribution.get("high_volume_advisor_ratio", 0.2)
            high_client_ratio = distribution.get("high_volume_client_ratio", 0.2)
            
            # Calculate number of high-volume advisors (excluding special cases)
            num_high_volume = max(1, int(len(remaining_advisors) * high_volume_ratio))
            high_volume_advisors = random.sample(remaining_advisors, num_high_volume)
            regular_advisors = [adv for adv in remaining_advisors if adv not in high_volume_advisors]
            
            # Assign clients to high-volume advisors (large client list)
            clients_per_high_volume = max(
                15,  # Minimum 15 clients (increased from 5)
                int((len(self.config.CLIENT_NAMES) * high_client_ratio) / len(high_volume_advisors))
            )
            
            # Assign clients to regular advisors (smaller client list)
            clients_per_regular = max(
                8,  # Minimum 8 clients (increased from 1)
                int((len(self.config.CLIENT_NAMES) * (1 - high_client_ratio)) / len(regular_advisors))
            ) if regular_advisors else 0
            
            # Assign clients
            for advisor in high_volume_advisors:
                self.client_advisor_map[advisor] = random.sample(
                    self.config.CLIENT_NAMES,
                    min(clients_per_high_volume, len(self.config.CLIENT_NAMES))
                )
                
            for advisor in regular_advisors:
                self.client_advisor_map[advisor] = random.sample(
                    self.config.CLIENT_NAMES,
                    min(clients_per_regular, len(self.config.CLIENT_NAMES))
                )
                
        else:  # uniform distribution
            # Distribute clients evenly
            clients_per_advisor = max(
                15,  # Minimum 15 clients per advisor (increased from 1)
                int(len(self.config.CLIENT_NAMES) * 0.7 / len(remaining_advisors))
            )
            
            for advisor in remaining_advisors:
                self.client_advisor_map[advisor] = random.sample(
                    self.config.CLIENT_NAMES,
                    min(clients_per_advisor, len(self.config.CLIENT_NAMES))
                )
        
        # Handle special cases
        for advisor in low_client_advisors:
            if advisor in self.client_advisor_map:
                # Assign very few clients (1-2)
                self.client_advisor_map[advisor] = random.sample(
                    self.config.CLIENT_NAMES,
                    min(random.randint(1, 2), len(self.config.CLIENT_NAMES))
                )
                
        for advisor in high_client_advisors:
            if advisor in self.client_advisor_map:
                # Assign many clients (40-60% of all clients)
                client_count = int(len(self.config.CLIENT_NAMES) * random.uniform(0.10, 0.20))
                self.client_advisor_map[advisor] = random.sample(
                    self.config.CLIENT_NAMES,
                    min(client_count, len(self.config.CLIENT_NAMES))
                )
        
        # Ensure every advisor has at least one client
        for advisor, clients in self.client_advisor_map.items():
            if not clients:
                self.client_advisor_map[advisor] = random.sample(
                    self.config.CLIENT_NAMES, 
                    min(1, len(self.config.CLIENT_NAMES))
                )
                
        # Log the distribution
        # client_counts = {advisor: len(clients) for advisor, clients in self.client_advisor_map.items()}
        # logging.info(f"Client-advisor distribution: {client_counts}")
        # logging.info(f"Initialized client-advisor map based on configuration.")
        # Log summary stats if complex distribution is used
        if self.config.CLIENT_ADVISOR_DISTRIBUTION.get("enabled", False):
             client_counts = {advisor: len(clients) for advisor, clients in self.client_advisor_map.items()}
             logging.info(f"Client distribution per advisor: Min={min(client_counts.values()) if client_counts else 0}, Max={max(client_counts.values()) if client_counts else 0}, Avg={sum(client_counts.values())/len(client_counts) if client_counts else 0:.1f}")


    def select_advisors_clients(self) -> Tuple[str, str]:
        """Select a random advisor-client pair (Unchanged - seems okay)."""
        # ... (Keep existing logic) ...
        if not hasattr(self, 'client_advisor_map'):
             self.initialize_client_advisor_map()

        advisor = random.choice(self.config.ADVISOR_NAMES)

        if advisor in self.client_advisor_map and self.client_advisor_map[advisor]:
             client = random.choice(self.client_advisor_map[advisor])
        else:
             logging.warning(f"Advisor '{advisor}' has no clients assigned in map, falling back to random client.")
             client = random.choice(self.config.CLIENT_NAMES)

        # logging.debug(f"Selected advisor-client pair: {advisor} - {client}") # Can be noisy
        return advisor, client

    def select_conversation_type(self) -> str:
        """Select a random conversation type (Unchanged - seems okay)."""
        # ... (Keep existing logic) ...
        conversation_type = random.choice(self.config.CONVERSATION_TYPES)
        # logging.debug(f"Selected conversation type: {conversation_type}") # Can be noisy
        return conversation_type

    def calculate_conversation_count(self):
        """Calculate conversation count based on config settings (Unchanged - seems okay)."""
        # ... (Keep existing logic) ...
        # Ensure NUM_CONVERSATIONS exists as a fallback
        default_num = getattr(self.config, 'NUM_CONVERSATIONS', 100) # Provide a default

        if not hasattr(self.config, 'DAILY_CONVERSATION_TARGET') or self.config.DAILY_CONVERSATION_TARGET is None:
             logging.info(f"Using NUM_CONVERSATIONS: {default_num}")
             return default_num

        if not hasattr(self.config, 'START_DATE') or not hasattr(self.config, 'END_DATE'):
             logging.warning("DAILY_CONVERSATION_TARGET requires START_DATE and END_DATE. Using NUM_CONVERSATIONS instead.")
             return default_num

        try:
            start = datetime.fromisoformat(self.config.START_DATE)
            end = datetime.fromisoformat(self.config.END_DATE)
            if end < start:
                 logging.error("END_DATE cannot be before START_DATE. Using NUM_CONVERSATIONS.")
                 return default_num
            days = (end - start).days + 1
        except ValueError:
             logging.error("Invalid START_DATE or END_DATE format. Using NUM_CONVERSATIONS.")
             return default_num

        calculated_count = int(days * self.config.DAILY_CONVERSATION_TARGET)

        # Handle enforcement preference
        enforce_exact = getattr(self.config, 'ENFORCE_EXACT_COUNT', False)
        if enforce_exact:
             if calculated_count != default_num:
                 logging.warning(f"Calculated count ({calculated_count}) differs from NUM_CONVERSATIONS ({default_num}). Using NUM_CONVERSATIONS due to ENFORCE_EXACT_COUNT=True.")
             return default_num
        else:
             logging.info(f"Using calculated conversation count: {calculated_count} ({self.config.DAILY_CONVERSATION_TARGET}/day for {days} days).")
             return calculated_count


    # --- MAJOR REFACTOR: generate_synthetic_data ---
    async def generate_synthetic_data(self):
        """
        Main method to generate synthetic data concurrently.
        """
        total_conversations_to_generate = self.calculate_conversation_count()
        self.config.NUM_CONVERSATIONS = total_conversations_to_generate # Ensure config reflects actual target

        logging.info(f"Starting synthetic data generation with run_id: {self.run_id}")
        logging.info(f"Targeting {total_conversations_to_generate} conversations.")
        logging.info(f"Concurrency level set to {self.max_concurrent_requests} requests.")

        # Initialize the LLM provider (ensure it's async and potentially sets up a session)
        await self.llm_provider.initialize()

        # Precalculate conversation distribution (remains the same)
        if self.datetime_strategy and hasattr(self.config, 'START_DATE') and hasattr(self.config, 'END_DATE'):
            # ... (your existing distribution calculation logic) ...
            pass

        # Log client-advisor distribution summary (remains the same)
        if hasattr(self, 'client_advisor_map'):
             # ... (your existing logging for distribution) ...
            pass

        tasks = []
        start_run_time = asyncio.get_event_loop().time()

        for i in range(total_conversations_to_generate):
            try:
                advisor_name, client_name = self.select_advisors_clients()
                conversation_type = self.select_conversation_type()
                num_messages = random.randint(self.config.MIN_MESSAGES, self.config.MAX_MESSAGES)

                # Create a task for processing this conversation
                task = asyncio.create_task(
                    self.process_conversation(
                        conv_index=i + 1, # Pass 1-based index
                        conversation_type=conversation_type,
                        advisor_name=advisor_name,
                        client_name=client_name,
                        num_messages=num_messages
                    ),
                    name=f"ConvTask_{i+1}" # Name the task for easier debugging
                )
                tasks.append(task)

                # When the number of tasks reaches the concurrency limit, run them
                if len(tasks) >= self.max_concurrent_requests:
                    await self._process_batch(tasks, total_conversations_to_generate)
                    tasks = [] # Reset tasks list for the next batch

            except Exception as e:
                # Catch errors during task *creation* (e.g., config issues)
                logging.error(f"Error creating task for conversation index {i+1}: {e}", exc_info=True)
                self.failed_conversations += 1 # Count as failed

        # Process any remaining tasks in the last batch
        if tasks:
            await self._process_batch(tasks, total_conversations_to_generate)

        # Final save of any remaining items in the buffer
        logging.info("Saving any remaining conversations from buffers...")
        self.save_conversation_files_from_buffer(force_save_all=True)

        end_run_time = asyncio.get_event_loop().time()
        total_duration = end_run_time - start_run_time
        logging.info("-" * 50)
        logging.info(f"Run {self.run_id} completed.")
        logging.info(f"Target conversations: {total_conversations_to_generate}")
        logging.info(f"Successfully generated: {self.completed_conversations}")
        logging.info(f"Failed generations: {self.failed_conversations}")
        logging.info(f"Total duration: {total_duration:.2f} seconds")
        if self.completed_conversations > 0:
             avg_time = total_duration / self.completed_conversations
             convs_per_sec = self.completed_conversations / total_duration if total_duration > 0 else 0
             logging.info(f"Average time per conversation: {avg_time:.3f} seconds")
             logging.info(f"Conversations per second: {convs_per_sec:.2f}")

        # --- Final Analytics Logging ---
        self._log_final_analytics()
        logging.info("-" * 50)


    async def _process_batch(self, tasks: List[asyncio.Task], total_target: int):
        """Helper function to run a batch of tasks and process results."""
        logging.info(f"Running batch of {len(tasks)} conversation generation tasks...")
        batch_start_time = asyncio.get_event_loop().time()

        # Run tasks concurrently and collect results or exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_duration = asyncio.get_event_loop().time() - batch_start_time
        logging.info(f"Batch completed in {batch_duration:.2f} seconds.")

        processed_in_batch = 0
        failed_in_batch = 0
        # Process results
        for i, result in enumerate(results):
            task_name = tasks[i].get_name() # Get task name if needed
            if isinstance(result, Exception):
                # Handle exceptions that occurred within process_conversation
                logging.error(f"Task {task_name} failed with exception: {result}", exc_info=result if isinstance(result, Exception) else False)
                self.failed_conversations += 1
                failed_in_batch += 1
            elif result is None:
                # Handle cases where process_conversation returned None (graceful failure)
                logging.warning(f"Task {task_name} did not return a conversation (likely an internal error or retry failure).")
                self.failed_conversations += 1
                failed_in_batch += 1
            else:
                # Successful conversation generation
                try:
                    advisor_name, client_name, conversation = result
                    buffer_key = f"{advisor_name}_{client_name}"

                    # Ensure buffer entry exists
                    if buffer_key not in self.conversation_files_buffer:
                        self.conversation_files_buffer[buffer_key] = ConversationFile(
                            version=self.config.JSON_VERSION,
                            advisor=advisor_name,
                            client=client_name,
                            conversations=[]
                        )

                    # Add conversation to the correct buffer
                    self.conversation_files_buffer[buffer_key].conversations.append(conversation)
                    self.completed_conversations += 1
                    processed_in_batch += 1

                    # Log success with details
                    conv_date = datetime.fromisoformat(conversation.timestamp)
                    logging.info(f"✓ Conv {conversation.conversation_id} | "
                                 f"Date: {conv_date.strftime('%Y-%m-%d %H:%M:%S')} | "
                                 f"Msgs: {len(conversation.lines)}")

                except Exception as e:
                     # Catch errors during result *processing*
                     logging.error(f"Error processing result for Task {task_name}: {e}", exc_info=True)
                     self.failed_conversations += 1
                     failed_in_batch += 1


        logging.info(f"Batch summary: {processed_in_batch} successful, {failed_in_batch} failed.")
        logging.info(f"Overall progress: {self.completed_conversations}/{total_target} completed.")

        # Check and save buffers periodically after processing a batch
        self.save_conversation_files_from_buffer(force_save_all=False)


    def _log_final_analytics(self):
        """Logs summary analytics at the end of the run."""
        logging.info("="*57)
        logging.info("\n" + "="*20 + " FINAL ANALYTICS " + "="*20)

        # Instantiate SummaryStatisticsLogger with the necessary data
        final_stats = SummaryStatisticsLogger(
            config=self.config,
            run_id=self.run_id,
            advisor_client_interactions=self.advisor_client_interactions,
            all_timestamps=self.all_timestamps,
            manifest_logger=self.manifest_logger,
            client_advisor_map=self.client_advisor_map,
            generation_strategy=self.generation_strategy # Add this line if you have it
        )

        # Call the methods to log the different types of statistics
        final_stats.log_advisor_client_distribution()

        if self.manifest_logger:
            final_stats.log_company_metrics()

        if self.all_timestamps:
            final_stats.log_temporal_distribution()

        logging.info("="*57)


    def _calculate_and_log_company_metrics(self):
        """Parses the manifest log file to calculate and log company metrics."""
        logging.info("\n===== COMPANY TARGETING METRICS =====")
        manifest_log_file = None
        if hasattr(self.config, 'CONVERSATION_MANIFEST_DIR') and self.manifest_logger:
            # Find the log file handler's path
            for handler in self.manifest_logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    manifest_log_file = Path(handler.baseFilename)
                    break

        if not manifest_log_file or not manifest_log_file.exists():
            logging.warning("Manifest log file not found or inaccessible. Cannot calculate company metrics.")
            return

        company_metrics = {
            'total_conversations_logged': 0,
            'targeted_conversations': 0,
            'targeted_with_mentions': 0,
            'total_mentions_in_targeted': 0,
            'mention_counts_in_targeted': Counter(),
            'conversations_by_mention_count': Counter(), # e.g., {1: 10, 2: 5, 3: 2}
        }

        try:
            with open(manifest_log_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        company_metrics['total_conversations_logged'] += 1

                        if data.get('company_targeting_enabled'):
                            company_metrics['targeted_conversations'] += 1
                            if data.get('has_company_mentions'):
                                company_metrics['targeted_with_mentions'] += 1
                                mentions_found = data.get('companies_found', [])
                                mention_count = len(mentions_found) # Number of unique companies found
                                actual_mention_count = data.get('company_mentions_found_count', 0) # Total mentions

                                company_metrics['total_mentions_in_targeted'] += actual_mention_count
                                company_metrics['mention_counts_in_targeted'].update(mentions_found)
                                company_metrics['conversations_by_mention_count'][mention_count] += 1

                    except json.JSONDecodeError:
                        logging.warning(f"Skipping malformed line in manifest log: {line.strip()}")
                    except Exception as e:
                         logging.warning(f"Error processing manifest line: {e} - Line: {line.strip()}")


            # --- Log Calculated Metrics ---
            total_conv = company_metrics['total_conversations_logged']
            targeted_conv = company_metrics['targeted_conversations']
            mentions_conv = company_metrics['targeted_with_mentions']

            # Config summary (optional, retrieve from strategy if possible)
            # logging.info(f"Config: Probability={...}, Min/Max={...}")

            if total_conv > 0:
                enabled_pct = (targeted_conv / total_conv * 100) if total_conv > 0 else 0
                logging.info(f"Conversations logged in manifest: {total_conv}")
                logging.info(f"Targeting enabled for: {targeted_conv} ({enabled_pct:.1f}%)")

            if targeted_conv > 0:
                success_pct = (mentions_conv / targeted_conv * 100) if targeted_conv > 0 else 0
                overall_pct = (mentions_conv / total_conv * 100) if total_conv > 0 else 0
                logging.info(f"Targeted conversations with >=1 mention found: {mentions_conv} ({success_pct:.1f}% hit rate)")
                logging.info(f"({overall_pct:.1f}% of all logged conversations)")

                if mentions_conv > 0:
                     avg_mentions = company_metrics['total_mentions_in_targeted'] / mentions_conv
                     logging.info(f"Avg mentions per conversation (when found): {avg_mentions:.2f}")

                # Distribution by number of unique companies found
                logging.info("\n----- Distribution by Unique Companies Found (in Targeted) -----")
                for num_companies, count in sorted(company_metrics['conversations_by_mention_count'].items()):
                     pct = (count / mentions_conv * 100) if mentions_conv > 0 else 0
                     bar = "█" * int(pct / 5)
                     logging.info(f"{num_companies} unique companies: {count} conversations ({pct:.1f}%) {bar}")


                # Top mentioned companies
                top_companies = company_metrics['mention_counts_in_targeted'].most_common(10)
                if top_companies:
                    logging.info("\n----- Top 10 Company Mentions (in Targeted) -----")
                    total_mentions = company_metrics['total_mentions_in_targeted']
                    for company, count in top_companies:
                        pct = (count / total_mentions * 100) if total_mentions > 0 else 0
                        bar = "█" * int(pct / 5)
                        logging.info(f"{company}: {count} mentions ({pct:.1f}%) {bar}")

                # Miss rate
                not_found = targeted_conv - mentions_conv
                if not_found > 0:
                    not_found_pct = (not_found / targeted_conv * 100) if targeted_conv > 0 else 0
                    logging.warning(f"\nTarget companies NOT found in {not_found} targeted conversations ({not_found_pct:.1f}% miss rate)")

        except FileNotFoundError:
            logging.warning("Manifest log file could not be opened. Cannot calculate company metrics.")
        except Exception as e:
            logging.error(f"Failed to calculate company metrics from manifest: {e}", exc_info=True)

