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

from .models.conversation import ConversationFile, SingleConversation, ChatLine
from .strategies.base import TaxonomyStrategy, GenerationStrategy, FewShotExampleStrategy
from .strategies.base.datetime_strategy import DatetimeStrategy
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
                 llm_provider: LLMProvider,
                 datetime_strategy: Optional[DatetimeStrategy] = None):
        """
        Initialize the generator with strategies and config.
        
        Args:
            config: Configuration settings
            taxonomy_strategy: Strategy for taxonomy processing
            generation_strategy: Strategy for conversation generation
            few_shot_strategy: Strategy for few-shot examples
            llm_provider: Provider for LLM integration
            datetime_strategy: Optional strategy for temporal distribution
        """
        self.config = config
        self.taxonomy_strategy = taxonomy_strategy
        self.generation_strategy = generation_strategy
        self.few_shot_strategy = few_shot_strategy
        self.llm_provider = llm_provider
        self.datetime_strategy = datetime_strategy
        
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
            
        # Track all timestamps for distribution analysis
        self.all_timestamps = []
    
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
        
        # Generate conversation timestamp using datetime strategy if available
        if self.datetime_strategy:
            conversation_timestamp = self.datetime_strategy.generate_conversation_timestamp(conv_number)
        else:
            conversation_timestamp = datetime.now().isoformat()
            
        # Track timestamp for distribution analysis
        self.all_timestamps.append(conversation_timestamp)
        
        # Create basic chat lines
        chat_lines = [ChatLine(**line) for line in conversation_lines]
        
        # Apply message timestamps if datetime strategy is available
        if self.datetime_strategy:
            message_timestamps = self.datetime_strategy.generate_message_timestamps(
                conversation_timestamp, len(chat_lines)
            )
            chat_lines = self.datetime_strategy.apply_timestamps_to_conversation(
                chat_lines, message_timestamps
            )
        
        conversation = SingleConversation(
            conversation_id=conversation_id,
            timestamp=conversation_timestamp,
            category=category,
            topic=formatted_topic,
            lines=chat_lines,
            company_mentions=manifest_blueprint.get("key_companies", [])
        )
        
        # Log manifest information
        self.log_conversation_manifest(
            conv_number, conversation_id, advisor_name, client_name,
            category, topic, subtopic, manifest_blueprint, conversation
        )
        
        # Enhanced time-related logging
        conv_date = datetime.fromisoformat(conversation.timestamp)
        
        # Calculate time elapsed for the conversation
        if len(chat_lines) > 1 and all(line.timestamp for line in chat_lines):
            first_msg_time = datetime.fromisoformat(chat_lines[0].timestamp)
            last_msg_time = datetime.fromisoformat(chat_lines[-1].timestamp)
            elapsed_seconds = (last_msg_time - first_msg_time).total_seconds()
            elapsed_str = f"{int(elapsed_seconds // 60)}m {int(elapsed_seconds % 60)}s"
        else:
            elapsed_str = "N/A"
            
        logging.info(f"Conversation {conv_number}: {conversation_id} | "
                    f"Date: {conv_date.strftime('%Y-%m-%d')} ({conv_date.strftime('%A')}) | "
                    f"Time: {conv_date.strftime('%H:%M:%S')} | "
                    f"Messages: {len(chat_lines)} | Elapsed: {elapsed_str}")
        
        logging.debug(f"Generated conversation {conversation_id} for {advisor_name}-{client_name} with {len(conversation_lines)} messages")
        
        return conversation
    
    def log_conversation_manifest(self, conv_number: int, conversation_id: str,
                                 advisor_name: str, client_name: str,
                                 category: str, topic: str, subtopic: str,
                                 manifest_blueprint: Dict[str, Any],
                                 conversation: SingleConversation):
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
            conversation: Generated conversation object
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
            "timestamp": conversation.timestamp,  # Use conversation timestamp
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
        
        # Precalculate conversation distribution if datetime strategy is available
        if self.datetime_strategy and hasattr(self.config, 'START_DATE') and hasattr(self.config, 'END_DATE'):
            time_period = (self.config.START_DATE, self.config.END_DATE)
            logging.info(f"Generating temporal distribution for time period: {time_period[0]} to {time_period[1]}")
            
            distribution = self.datetime_strategy.get_message_count_distribution(
                time_period, self.config.NUM_CONVERSATIONS
            )
            
            # Log the distribution summary by month
            monthly_summary = {}
            for date_str, count in distribution.items():
                month = date_str[:7]  # Extract YYYY-MM
                if month not in monthly_summary:
                    monthly_summary[month] = 0
                monthly_summary[month] += count
                
            logging.info(f"Conversation distribution by month: {monthly_summary}")
        
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
        
        # Log summary of temporal distribution
        if hasattr(self, 'all_timestamps') and self.all_timestamps:
            # Group by date
            date_counts = {}
            for ts in self.all_timestamps:
                date_str = datetime.fromisoformat(ts).date().isoformat()
                if date_str not in date_counts:
                    date_counts[date_str] = 0
                date_counts[date_str] += 1
                
            # Group by month
            month_counts = {}
            for ts in self.all_timestamps:
                dt = datetime.fromisoformat(ts)
                month_str = dt.strftime('%Y-%m')  # Format: YYYY-MM
                if month_str not in month_counts:
                    month_counts[month_str] = 0
                month_counts[month_str] += 1
            
            # Group by week
            week_counts = {}
            for ts in self.all_timestamps:
                dt = datetime.fromisoformat(ts)
                week_num = dt.isocalendar()[1]  # ISO week number
                week_str = f"{dt.year}-W{week_num:02d}"
                if week_str not in week_counts:
                    week_counts[week_str] = 0
                week_counts[week_str] += 1
            
            # Group by day of week
            day_counts = {'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 
                         'Thursday': 0, 'Friday': 0, 'Saturday': 0, 'Sunday': 0}
            weekday_by_month = {}  # Track weekday distribution by month
            for ts in self.all_timestamps:
                dt = datetime.fromisoformat(ts)
                day_name = dt.strftime('%A')
                day_counts[day_name] += 1
                
                # Track weekday by month
                month_str = dt.strftime('%Y-%m')
                if month_str not in weekday_by_month:
                    weekday_by_month[month_str] = {day: 0 for day in day_counts.keys()}
                weekday_by_month[month_str][day_name] += 1
                
            # Group by hour
            hour_counts = {h: 0 for h in range(24)}
            for ts in self.all_timestamps:
                hour = datetime.fromisoformat(ts).hour
                hour_counts[hour] += 1
            
            # Calculate date range and total days
            sorted_dates = sorted(date_counts.items())
            first_date = datetime.fromisoformat(sorted_dates[0][0] + "T00:00:00").date()
            last_date = datetime.fromisoformat(sorted_dates[-1][0] + "T00:00:00").date()
            total_days = (last_date - first_date).days + 1
            
            # Calculate days with conversations
            days_with_conversations = len(date_counts)
            coverage_percentage = (days_with_conversations / total_days) * 100 if total_days > 0 else 0
            
            # Log the distributions
            logging.info("\n===== TEMPORAL DISTRIBUTION SUMMARY =====")
            logging.info(f"Total conversations generated: {len(self.all_timestamps)}")
            logging.info(f"Date range: from {sorted_dates[0][0]} to {sorted_dates[-1][0]} ({total_days} days)")
            logging.info(f"Days with conversations: {days_with_conversations} ({coverage_percentage:.1f}% coverage)")
            
            # Log monthly distribution
            logging.info("\n----- Monthly Distribution -----")
            for month, count in sorted(month_counts.items()):
                percentage = (count / len(self.all_timestamps)) * 100
                bar = "█" * int(percentage / 5)  # Visual bar (each █ = 5%)
                logging.info(f"{month}: {count} conversations ({percentage:.1f}%) {bar}")
            
            # Log weekly distribution
            logging.info("\n----- Weekly Distribution -----")
            for week, count in sorted(week_counts.items()):
                percentage = (count / len(self.all_timestamps)) * 100
                bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
                logging.info(f"{week}: {count} conversations ({percentage:.1f}%) {bar}")
            
            # Log day of week distribution
            logging.info("\n----- Day of Week Distribution -----")
            for day, count in day_counts.items():
                percentage = (count / len(self.all_timestamps)) * 100
                bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
                logging.info(f"{day}: {count} conversations ({percentage:.1f}%) {bar}")
            
            # Log day of week by month (if multiple months)
            if len(month_counts) > 1:
                logging.info("\n----- Day of Week Distribution by Month -----")
                for month, days in sorted(weekday_by_month.items()):
                    logging.info(f"\nMonth: {month}")
                    month_total = sum(days.values())
                    for day, count in days.items():
                        percentage = (count / month_total) * 100 if month_total > 0 else 0
                        bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
                        logging.info(f"  {day}: {count} conversations ({percentage:.1f}%) {bar}")
            
            # Format hour distribution with visual bar
            logging.info("\n----- Hour Distribution -----")
            max_hour_count = max(hour_counts.values()) if hour_counts else 0
            for hour in sorted(hour_counts.keys()):
                count = hour_counts[hour]
                if count > 0:
                    percentage = (count / len(self.all_timestamps)) * 100
                    bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
                    hour_str = f"{hour:02d}:00"
                    logging.info(f"{hour_str}: {count} conversations ({percentage:.1f}%) {bar}")
            
            # Generate date-based histogram for longer periods
            if total_days > 10 and total_days <= 90:  # For medium-length periods (up to 3 months)
                logging.info("\n----- Daily Distribution Histogram -----")
                # Create a continuous date range
                current_date = first_date
                while current_date <= last_date:
                    date_str = current_date.isoformat()
                    count = date_counts.get(date_str, 0)
                    day_name = current_date.strftime('%a')  # Abbreviated day name
                    
                    # Calculate visual representation
                    if len(self.all_timestamps) > 0:
                        max_count = max(date_counts.values())
                        bar_length = min(20, max(1, int((count / max_count) * 20))) if max_count > 0 else 0
                        bar = "█" * bar_length
                    else:
                        bar = ""
                        
                    logging.info(f"{date_str} ({day_name}): {count:2d} {bar}")
                    current_date += timedelta(days=1)
            
            # For very long periods, generate a condensed view by week
            elif total_days > 90:
                logging.info("\n----- Weekly Distribution Histogram -----")
                # Group dates by week for visualization
                week_of_year = {}
                for date_str, count in date_counts.items():
                    dt = datetime.fromisoformat(date_str + "T00:00:00")
                    year, week_num, _ = dt.isocalendar()
                    week_key = f"{year}-W{week_num:02d}"
                    
                    if week_key not in week_of_year:
                        week_of_year[week_key] = {
                            'count': 0,
                            'start_date': None,
                            'end_date': None
                        }
                    
                    week_of_year[week_key]['count'] += count
                    
                    # Track start and end dates of the week
                    if week_of_year[week_key]['start_date'] is None or dt.date() < week_of_year[week_key]['start_date']:
                        week_of_year[week_key]['start_date'] = dt.date()
                    
                    if week_of_year[week_key]['end_date'] is None or dt.date() > week_of_year[week_key]['end_date']:
                        week_of_year[week_key]['end_date'] = dt.date()
                
                # Display histogram
                max_week_count = max([w['count'] for w in week_of_year.values()]) if week_of_year else 0
                
                for week_key, data in sorted(week_of_year.items()):
                    count = data['count']
                    start_date = data['start_date'].isoformat() if data['start_date'] else "Unknown"
                    end_date = data['end_date'].isoformat() if data['end_date'] else "Unknown"
                    
                    # Calculate visual representation
                    bar_length = min(20, max(1, int((count / max_week_count) * 20))) if max_week_count > 0 else 0
                    bar = "█" * bar_length
                    
                    logging.info(f"{week_key} ({start_date} to {end_date}): {count:3d} conversations {bar}")
            
            # Show day-by-day summary if we have a very small number of days
            elif total_days <= 10:
                logging.info("\n----- Daily Distribution -----")
                for date_str, count in sorted_dates:
                    day_name = datetime.fromisoformat(date_str + "T00:00:00").strftime('%A')
                    percentage = (count / len(self.all_timestamps)) * 100
                    bar = "█" * int(percentage / 2)  # Visual bar (each █ = 2%)
                    logging.info(f"{date_str} ({day_name}): {count} conversations ({percentage:.1f}%) {bar}")
            
            # Write summary to a separate file for easier analysis
            try:
                summary_path = Path(self.config.OUTPUT_DIR) / f"temporal_summary_{self.run_id}.txt"
                with open(summary_path, 'w') as f:
                    f.write("===== TEMPORAL DISTRIBUTION SUMMARY =====\n")
                    f.write(f"Total conversations: {len(self.all_timestamps)}\n")
                    f.write(f"Date range: {sorted_dates[0][0]} to {sorted_dates[-1][0]} ({total_days} days)\n\n")
                    
                    f.write("--- Daily Distribution ---\n")
                    for date_str, count in sorted_dates:
                        f.write(f"{date_str}: {count}\n")
                        
                logging.info(f"\nDetailed temporal distribution summary written to: {summary_path}")
            except Exception as e:
                logging.warning(f"Could not write temporal summary file: {e}")
        
        logging.info(f"Completed synthetic data generation. Generated {self.config.NUM_CONVERSATIONS} conversations.")