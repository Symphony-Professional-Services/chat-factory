import os
import json
import random
import logging
import csv
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import uuid
from datetime import datetime
import argparse
import google
import asyncio
from google.cloud import aiplatform  # might be outdated package import INSPECT
#import aiplatform

import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from vertexai.preview.language_models import ChatSession
import inspect
import config

# Setup Logging
logging.basicConfig(
    filename=config.LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class ChatLine:
    speaker: str  # "0" = client, "1" = advisor
    text: str

@dataclass
class SingleConversation:
    conversation_id: str
    timestamp: str
    category: str  # Top-level category
    topic: str     # Will now contain "topic.subtopic" if applicable
    lines: List[ChatLine] = field(default_factory=list)
    company_mentions: List[str] = field(default_factory=list)  # Add company mentions field

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "topic": self.topic,
            "lines": [line.__dict__ for line in self.lines],
            "company_mentions": self.company_mentions  # Include company mentions in output
        }

@dataclass
class ConversationFile:
    version: str
    advisor: str
    client: str
    conversations: List[SingleConversation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "advisor": self.advisor,
            "client": self.client,
            "conversations": [conv.to_dict() for conv in self.conversations]
        }

def sanitize_filename(name: str) -> str:
    """
    Removes or replaces characters that are invalid in filenames.
    """
    return re.sub(r'[<>:"/\\|?*]', '', name)

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, help="Optional run id to use for this generation")
    return parser.parse_args()


class SyntheticChatGenerator:
    def __init__(self, config, run_id=None):

        self.personas = config.PERSONAS
        self.conversation_types = config.CONVERSATION_TYPES
        self.message_formats = config.MESSAGE_FORMATS
        self.message_length_ratio = config.MESSAGE_LENGTH_RATIO
        self.few_shot_examples_dir = Path(config.FEW_SHOT_EXAMPLES_DIR)
        self.company_data_file = config.COMPANY_DATA_FILE
        
        # Load company targeting configuration
        self.company_targeting = getattr(config, 'COMPANY_TARGETING', {
            "enabled": True,
            "probability": 0.8,
            "min_companies": 1,
            "max_companies": 3
        })
        logging.info(f"Company targeting configuration: {self.company_targeting}")

        self.temperature = config.TEMPERATURE
        self.top_p = config.TOP_P
        self.top_k = config.TOP_K

        self.project_id = config.PROJECT_ID
        self.location = config.LOCATION
        self.model_name = config.MODEL_NAME.lower()
        
        # Load taxonomy file - could be either financial advisor or company tagging format
        self.taxonomy_file = config.TAXONOMY_FILE
        
        self.advisor_names = config.ADVISOR_NAMES  
        self.client_names = config.CLIENT_NAMES      
        self.json_version = config.JSON_VERSION
        self.num_conversations = config.NUM_CONVERSATIONS
        self.min_messages = config.MIN_MESSAGES
        self.max_messages = config.MAX_MESSAGES
        self.topic_distribution = config.TOPIC_DISTRIBUTION

        # Load taxonomy and detect its format
        self.taxonomy = self._load_taxonomy(self.taxonomy_file)
        self.taxonomy_format = self.detect_taxonomy_format(self.taxonomy)
        logging.info(f"Detected taxonomy format: {self.taxonomy_format}")
        
        if self.taxonomy_format == "company_tagging":
            self.flattened_topics = self.flatten_taxonomy(self.taxonomy)
            # For company tagging, use the conversation type as both category and topic
            self.conversation_type_metadata = self.taxonomy.get("conversation_types", {})
            logging.info(f"Loaded {len(self.conversation_type_metadata)} conversation types from company tagging taxonomy")
        else:  # financial advisor taxonomy format
            self.flattened_topics = self.flatten_taxonomy(self.taxonomy)  # Now includes subtopics
            # For financial advisor taxonomy, no conversation type metadata available
            self.conversation_type_metadata = {}
        
        # Use provided run_id if given; otherwise, generate a new one.
        if run_id:
            self.run_id = run_id
        else:
            #self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
            self.run_id = "temp"
        logging.info(f"Using run_id: {self.run_id}")

        self.output_dir_base = Path(config.OUTPUT_DIR)

        self.output_dir = self.setup_output_directory()
        self.setup_output_directory()
        self.initialize_vertex_ai()
        self.conversation_buffer = {}

        self.company_data = self.load_company_data()
        logging.info("--- Credential Verification Logging ---")

        # Use a single directory for both conversation scripts and manifests
        self.conversation_manifest_dir = Path(config.CONVERSATION_MANIFEST_DIR)
        self.conversation_manifest_dir.mkdir(parents=True, exist_ok=True)

        #Create a dedicated logger for conversation manifests with run_id in the file name
        self.manifest_logger = logging.getLogger("conversation_manifest")
        self.manifest_logger.setLevel(logging.INFO)
        if not self.manifest_logger.handlers:
            manifest_log_file = self.conversation_manifest_dir / f"conversation_manifest_{self.run_id}.log"
            fh = logging.FileHandler(manifest_log_file)
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.manifest_logger.addHandler(fh)

    def _load_taxonomy(self, taxonomy_file: str, taxonomy_type: str = None) -> Dict[str, Any]:
        """
        Load the taxonomy file for the specified type.
        If taxonomy_type is not specified, it will be determined from the config.
        """
        logging.info(f"Loading taxonomy from file: {taxonomy_file}")
        
        try:
            with open(taxonomy_file, 'r') as f:
                taxonomy = json.load(f)
            
            # Validate the taxonomy structure based on the type
            if not taxonomy:
                logging.error(f"Empty taxonomy loaded from {taxonomy_file}")
                return {}
                
            logging.info(f"Successfully loaded taxonomy with {len(taxonomy)} top-level categories")
            
            # For debugging
            if "conversation_types" in taxonomy:
                logging.info(f"Detected company_tagging taxonomy format with {len(taxonomy.get('conversation_types', {}))} conversation types")
                for conv_type, data in taxonomy.get("conversation_types", {}).items():
                    if isinstance(data, dict) and "company_count_options" in data:
                        logging.info(f"  - {conv_type}: company_count_options={data['company_count_options']}")
            else:
                # Log the structure of the financial advisor taxonomy
                for category, items in taxonomy.items():
                    if isinstance(items, dict):
                        subcats_count = len(items)
                        topics_count = sum(len(topics) for topics in items.values() if isinstance(topics, list))
                        logging.info(f"  - {category}: {subcats_count} subcategories, {topics_count} total topics")
                    elif isinstance(items, list):
                        logging.info(f"  - {category}: {len(items)} topics")
            
            return taxonomy
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error loading taxonomy file {taxonomy_file}: {e}")
            return {}

    def load_company_data(self, force_load=False) -> List[Dict]:
        """
        Load company data from CSV file.
        
        Args:
            force_load: If True, attempt to load even if company targeting is disabled
            
        Returns:
            List of company data dictionaries
        """
        # Skip loading if company targeting is disabled and not force_load
        if not self.company_targeting.get("enabled", True) and not force_load:
            logging.info("Company targeting is disabled. Skipping company data loading.")
            return []
            
        # If company data file path is empty, return empty list
        if not self.company_data_file:
            logging.warning("Company data file path is empty. Cannot load company data.")
            return []
            
        try:
            if not os.path.exists(self.company_data_file):
                logging.error(f"Company data file not found: {self.company_data_file}")
                return []
                
            # Load company data from CSV
            import csv
            company_data = []
            with open(self.company_data_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    company_data.append(row)
            logging.info(f"Loaded {len(company_data)} companies from {self.company_data_file}")
            return company_data
        except Exception as e:
            logging.error(f"Error loading company data file: {e}")
            return []

    def detect_taxonomy_format(self, taxonomy: Dict[str, Any]) -> str:
        if "conversation_types" in taxonomy:
            return "company_tagging"
        else:
            return "financial_advisor"

    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        Flatten the taxonomy structure into a list of tuples.
        For financial advisor taxonomy: (category, topic, subtopic)
        For company tagging taxonomy: (conversation_type, conversation_type, "")
        """
        logging.info("Flattening taxonomy structure")
        flattened = []
        
        # Check if we have a company tagging taxonomy
        if self.taxonomy_format == "company_tagging":
            conversation_types = taxonomy.get("conversation_types", {})
            for conv_type in conversation_types.keys():
                # For company tagging, use the conversation type as both category and topic
                flattened.append((conv_type, conv_type, ""))
            logging.info(f"Flattened company tagging taxonomy into {len(flattened)} conversation types")
            return flattened
        
        # Financial advisor taxonomy structure processing
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
        
        logging.info(f"Flattened financial advisor taxonomy into {len(flattened)} unique topic paths")
        # Log some sample topics for debugging
        if flattened:
            sample_topics = flattened[:3] if len(flattened) > 3 else flattened
            logging.info(f"Sample topics: {sample_topics}")
        
        return flattened

    def select_topic(self) -> Tuple[str, str, str]:
        """
        Select a random topic from the flattened taxonomy.
        Returns a tuple of (category, topic, subtopic)
        """
        if not self.flattened_topics:
            logging.warning("No flattened topics available. Using default topic.")
            return ("General", "General Conversation", "")
        
        # Select a random topic
        category, topic, subtopic = random.choice(self.flattened_topics)
        
        logging.info(f"Selected topic: category='{category}', topic='{topic}', subtopic='{subtopic}'")
        
        return category, topic, subtopic

    def select_conversation_type(self) -> str:
        conversation_type = random.choice(self.conversation_types)
        logging.debug(f"Selected conversation type: {conversation_type}")
        return conversation_type

    def get_message_format(self, conversation_type: str) -> str:
        message_format = self.message_formats.get(conversation_type, "formal")
        logging.debug(f"Message format for {conversation_type}: {message_format}")
        return message_format

    def select_persona(self) -> str:
        """
        Randomly select a persona from the available personas.
        """
        if not self.personas:
            logging.warning("No personas available, using default")
            return "Financial Advisor"
        return random.choice(self.personas)

    def select_advisors_clients(self) -> Tuple[str, str]:
        advisor = random.choice(self.advisor_names)
        client = random.choice(self.client_names)
        logging.debug(f"Selected advisor-client pair: {advisor} - {client}")
        return advisor, client

    def assign_random_attributes(self) -> Tuple[int, str]:
        age = random.randint(30, 60)
        communication_style = random.choice([
            "Professional yet approachable",
            "Analytical and detailed",
            "Friendly and engaging",
            "Straightforward and pragmatic",
            "Calm and reassuring",
            "Energetic and enthusiastic",
            "Assertive and confident",
            "Informal yet professional",
            "Direct and inquisitive",
            "Casual but focused",
            "Strategic and decisive",
            "Compassionate and thoughtful",
            "Innovative and forward-thinking",
            "Pragmatic and detail-oriented",
            "Analytical and thorough",
            "Energetic and engaging"
        ])
        return age, communication_style

    async def call_vertex_ai(self, prompt: str, max_retries: int = 10, initial_backoff: float = 1.0, max_backoff: float = 32.0) -> str:
        """
        Call Vertex AI with exponential backoff retry logic for handling rate limits (429 errors).
        
        Args:
            prompt: The prompt to send to the LLM
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            
        Returns:
            The text response from the LLM or empty string on failure
        """
        backoff = initial_backoff
        attempt = 0
        
        while attempt <= max_retries:
            try:
                attempt += 1
                generation_config = GenerationConfig(
                    max_output_tokens=1200,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    top_k=self.top_k
                )
                
                if attempt > 1:
                    logging.info(f"Vertex AI API call attempt {attempt}/{max_retries+1}")
                
                response = await self.llm.generate_content_async(
                    contents=[prompt],
                    generation_config=generation_config,
                    stream=False
                )
                raw_response = response.candidates[0].content.text.strip()
                logging.debug(f"Raw LLM Response: {raw_response}")
                return raw_response
                
            except Exception as e:
                error_message = str(e)
                
                # Check if this is a rate limit error (429)
                if "429" in error_message or "quota" in error_message.lower() or "rate limit" in error_message.lower():
                    if attempt <= max_retries:
                        # Calculate backoff with jitter (up to 25% randomness)
                        jitter = random.uniform(0, 0.25 * backoff)
                        sleep_time = backoff + jitter
                        
                        logging.warning(f"Rate limit (429) hit. Retrying in {sleep_time:.2f} seconds (attempt {attempt}/{max_retries+1})")
                        await asyncio.sleep(sleep_time)
                        
                        # Exponential backoff with truncation
                        backoff = min(backoff * 2, max_backoff)
                    else:
                        logging.error(f"Maximum retry attempts ({max_retries+1}) reached for rate limit errors.")
                        return ""
                else:
                    # For non-rate-limit errors, log and return immediately
                    logging.error(f"Error calling Vertex AI: {e}", exc_info=True)
                    return ""
        
        # This point is reached if we've exhausted all retries
        logging.error(f"Failed to get a response from Vertex AI after {max_retries+1} attempts")
        return ""

    def get_company_name_variations(self) -> Dict[str, List[str]]:
        company_variations = {}
        for company_data_item in self.company_data:
            company_name = company_data_item['name']
            variations = company_data_item.get('variations', [])
            abbreviations = company_data_item.get('abbreviations', [])
            misspellings = company_data_item.get('misspellings', [])
            ticker = company_data_item.get('ticker')
            all_variations = set([company_name] + variations + abbreviations + misspellings)
            if ticker:
                all_variations.add(ticker)
            company_variations[company_name] = list(all_variations)
        return company_variations

    def select_company_count(self, conversation_type: str) -> int:
        """
        Select the number of companies to include in a conversation based on the conversation type.
        For company_tagging taxonomy, this will use the company_count_options field.
        Otherwise, it falls back to the global config values.
        """
        if not self.company_targeting.get("enabled", False):
            logging.debug(f"Company targeting disabled by config. Returning 0 companies for {conversation_type}")
            return 0

        # If we have a company_tagging taxonomy, use the conversation_type_metadata to determine company count
        if self.taxonomy_format == "company_tagging":
            conversation_metadata = self.conversation_type_metadata.get(conversation_type, {})
            company_count_options = conversation_metadata.get("company_count_options", [])
            
            if company_count_options:
                logging.info(f"Found company_count_options for {conversation_type}: {company_count_options}")
                # Select a random count from the options
                count = random.choice(company_count_options)
                logging.info(f"Selected {count} companies for {conversation_type} based on taxonomy values")
                return count
        
        # Fall back to global config if no specific options found
        min_companies = self.company_targeting.get("min_companies", 1)
        max_companies = self.company_targeting.get("max_companies", 3)
        count = random.randint(min_companies, max_companies)
        logging.info(f"Selected {count} companies for {conversation_type} based on config values")
        return count

    def create_manifest_blueprint(self, conversation_type: str, num_messages: int, category: str = "", topic: str = "") -> dict:
        """
        Create a conversation blueprint for use in prompting. The blueprint is a dictionary
        containing the details for how the conversation should unfold, including any 
        key companies that should be discussed.
        """
        num_key_companies = self.select_company_count(conversation_type)
        company_targeting_enabled = num_key_companies > 0
        
        # Get conversation flow characteristics based on the conversation type
        flow_characteristics = {}
        if self.taxonomy_format == "company_tagging" and conversation_type in self.conversation_type_metadata:
            conv_meta = self.conversation_type_metadata[conversation_type]
            flow_characteristics = {
                "description": conv_meta.get("description", ""),
                "message_format": conv_meta.get("message_format", "formal"),
                "message_style": conv_meta.get("message_style", ""),
                "typical_message_length": conv_meta.get("typical_message_length", "medium")
            }
            logging.info(f"Using conversation flow characteristics from company tagging taxonomy for {conversation_type}")
        else:
            # Default flow characteristics if not found in taxonomy
            flow_characteristics = {
                "message_format": "formal",
                "message_style": "professional, analytical",
                "typical_message_length": "medium"
            }
            logging.info(f"Using default conversation flow characteristics for {conversation_type}")
        
        # Define conversation length based on the number of messages
        conversation_length = "medium"
        if num_messages < 8:
            conversation_length = "short"
        elif num_messages > 12:
            conversation_length = "long"
            
        # Adjust conversation flow based on whether companies are included
        if company_targeting_enabled:
            conversation_flow = [
                {"speaker": "advisor", "topic": "Initial market overview"},
                {"speaker": "client", "topic": "Questions about specific companies"},
                {"speaker": "advisor", "topic": "Analysis of earnings and performance"},
                {"speaker": "client", "topic": "Follow-up and comparison"}
            ]
        else:
            # Generic conversation flow when no companies are targeted
            conversation_flow = [
                {"speaker": "advisor", "topic": "Initial greeting and discussion"},
                {"speaker": "client", "topic": "General questions or concerns"},
                {"speaker": "advisor", "topic": "Professional advice or information"},
                {"speaker": "client", "topic": "Follow-up questions or closing"}
            ]
        
        # Base blueprint with conversation flow characteristics
        blueprint = {
            "conversation_type": conversation_type,
            "num_messages": num_messages,
            "flow_characteristics": flow_characteristics,
            "company_targeting_enabled": company_targeting_enabled,
            "conversation_length": conversation_length,
            "persona_advisor": self.select_persona(),
            "persona_client": self.select_persona(),
            "conversation_flow": conversation_flow,
            "key_companies": []  # Initialize with empty list by default
        }
        
        # Add category and topic information to the blueprint
        blueprint["category"] = category
        blueprint["topic"] = topic
        
        # If no companies should be targeted, return the blueprint as is
        if not company_targeting_enabled:
            return blueprint
        
        # Only attempt to load company data if targeting is enabled
        company_data = self.load_company_data()
        if not company_data:
            logging.warning("No company data available, but company targeting is enabled. Check COMPANY_DATA_FILE setting.")
            return blueprint
        
        # Select n random companies based on the number determined by select_company_count
        sampled_companies = random.sample(company_data, min(num_key_companies, len(company_data)))
        
        # Format the company data properly
        key_companies = []
        for company_dict in sampled_companies:
            # Extract company details correctly
            official_name = company_dict.get("name", "Unknown")
            extracted_entity = company_dict.get("formal_name", official_name)
            ticker = company_dict.get("ticker", "Unknown")
            
            key_companies.append({
                "extracted_entity": extracted_entity,
                "official_name": official_name,
                "ticker": ticker
            })
        
        # Add company details to the blueprint
        blueprint["key_companies"] = key_companies
        
        # Log the selected companies
        company_names = [company.get("official_name", "Unknown") for company in key_companies]
        logging.info(f"Selected {len(key_companies)} companies for {conversation_type}: {', '.join(company_names)}")
        
        return blueprint

    def construct_prompt(
        self,
        advisor_name: str,
        client_name: str,
        conversation_type: str,
        num_messages: int,
        manifest_blueprint: dict
    ) -> str:
        """
        Constructs the prompt for the LLM based on the blueprint.
        """
        # Get topic details from the manifest
        category = manifest_blueprint.get("category", "General")
        topic_with_subtopic = manifest_blueprint.get("topic", "General Conversation")
        
        # Split the topic.subtopic format
        topic_parts = topic_with_subtopic.split('.')
        main_topic = topic_parts[0]
        subtopic = topic_parts[1] if len(topic_parts) > 1 else ""
        
        logging.info(f"Constructing prompt with category={category}, main_topic={main_topic}, subtopic={subtopic}")

        # Retrieve the key companies if targeting is enabled
        company_targeting_enabled = manifest_blueprint.get("company_targeting_enabled", False)
        key_companies = manifest_blueprint.get("key_companies", [])
        
        # Determine message distribution
        message_length_guidance = self.get_message_length_guidance(num_messages)
        
        # Build the system prompt
        prompt_header = f"""
You are a helpful assistant that generates realistic simulated conversations. 
Your task is to create a detailed synthetic conversation between an advisor named {advisor_name} and a client named {client_name}.

This is a {conversation_type} conversation. The conversation should be between {num_messages} messages total.
"""

        # Add company targeting instructions if enabled
        if company_targeting_enabled and key_companies:
            company_names = [company.get("official_name", "") for company in key_companies]
            prompt_header += f"""
The conversation should naturally mention the following companies: {', '.join(company_names)}.
Ensure that these companies are integrated naturally into the conversation topic.
"""

        # Build the conversation details
        prompt_body = f"""
Please generate a realistic conversation with the following details:

Conversation Type: {conversation_type}
Conversation Category: {category}
Topic Area: {main_topic}
"""
        # Add subtopic if available
        if subtopic:
            prompt_body += f"Specific Topic: {subtopic}\n"
            
        prompt_body += f"""
Number of Messages: {num_messages}
Client: {client_name}
Advisor: {advisor_name}

Conversation Flow:
"""

        # Add message length guidance
        for i, length in enumerate(message_length_guidance):
            speaker = advisor_name if i % 2 == 0 else client_name
            speaker_id = "0" if i % 2 == 0 else "1"
            prompt_body += f"- Message {i+1}: Speaker {speaker_id} ({speaker}), Length: {length}\n"

        # Additional instructions on companies if targeting is enabled
        if company_targeting_enabled and key_companies:
            prompt_body += "\nCompany References:\n"
            for company in key_companies:
                prompt_body += f"- {company.get('official_name', '')}: {company.get('description', 'No description available')}\n"

        # Add formatting instructions
        prompt_body += """
Output the conversation as a JSON object with a 'conversations' array containing messages with 'speaker' and 'text' fields.
Place the entire JSON within <BEGIN CONVERSATION> and <END CONVERSATION> tags.

<BEGIN CONVERSATION>
{
    "conversations": [
        {
            "speaker": "0",
            "text": "Hello, how can I help you today?"
        },
        {
            "speaker": "1",
            "text": "I'm interested in discussing some investment options."
        }
        // more messages...
    ]
}
<END CONVERSATION>

Speakers should be represented by "0" (the advisor) and "1" (the client). Ensure the conversation is realistic, engaging, and adheres to the topic.
"""

        full_prompt = prompt_header + prompt_body
        logging.debug(f"Constructed Prompt: {full_prompt}")
        return full_prompt

    def parse_response(self, response: str, expected_messages: int) -> List[ChatLine]:
        try:
            start_tag = "<BEGIN CONVERSATION>"
            end_tag = "<END CONVERSATION>"

            start = response.find(start_tag)
            end = response.find(end_tag)

            if start == -1 or end == -1:
                logging.error(f"Missing conversation tags in the LLM response (in {__file__}:{inspect.currentframe().f_lineno}).")
                logging.debug(f"Full LLM Response: {response}")
                return []

            json_str = response[start + len(start_tag):end].strip()

            # If the output starts with an array, wrap it in an object.
            if json_str.startswith("["):
                logging.warning(f"LLM returned a JSON array instead of an object (in {__file__}:{inspect.currentframe().f_lineno}). Wrapping array in {{'conversations': ...}}.")
                data = {"conversations": json.loads(json_str)}
            elif json_str.startswith("{"):
                data = json.loads(json_str)
            else:
                logging.error(f"Expected a JSON object (starting with '{{') but did not find one (in {__file__}:{inspect.currentframe().f_lineno}).")
                logging.debug(f"Extracted JSON string: {json_str}")
                return []

            if not isinstance(data, dict):
                logging.error(f"Parsed JSON is not an object as expected (in {__file__}:{inspect.currentframe().f_lineno}).")
                logging.debug(f"Parsed JSON data: {data}")
                return []

            if "conversations" not in data or not isinstance(data["conversations"], list):
                logging.error(f"JSON object missing key 'conversations' or it is not a list (in {__file__}:{inspect.currentframe().f_lineno}).")
                logging.debug(f"Parsed JSON data: {data}")
                return []

            lines = []
            for index, message in enumerate(data["conversations"]):
                if not isinstance(message, dict):
                    logging.error(f"Message at index {index} is not a dictionary (in {__file__}:{inspect.currentframe().f_lineno}).")
                    continue
                if "speaker" not in message or "text" not in message:
                    logging.error(f"Message at index {index} missing required keys 'speaker' or 'text' (in {__file__}:{inspect.currentframe().f_lineno}).")
                    continue
                text = message["text"].encode('utf-8', 'ignore').decode('utf-8')
                lines.append(ChatLine(speaker=message["speaker"], text=text))

            if len(lines) != expected_messages:
                logging.warning(f"Expected {expected_messages} messages, but got {len(lines)} (in {__file__}:{inspect.currentframe().f_lineno}).")

            return lines

        except json.JSONDecodeError as e:
            logging.exception(f"JSON decoding error while parsing LLM response (in {__file__}:{inspect.currentframe().f_lineno}): {e}")
            logging.debug(f"Malformed JSON: {response}")
            return []
        except Exception as e:
            logging.exception(f"Unexpected error while parsing LLM response (in {__file__}:{inspect.currentframe().f_lineno}): {e}")
            logging.debug(f"Response content: {response}")
            return []

    async def process_conversation(
        self,
        conv_number: int,
        conversation_type: str,
        advisor_name: str,
        client_name: str,
        num_messages: int
    ) -> SingleConversation:
        """
        Processes and buffers a single conversation.
        """
        try:
            timestamp = datetime.now().isoformat()
            category, topic, subtopic = self.select_topic()
            conversation_id = f"{self.run_id}_{conv_number}_{uuid.uuid4().hex[:8]}"

            # Format the topic in the desired format
            formatted_topic = f"{topic}.{subtopic}" if subtopic else topic

            # Create the manifest blueprint with company targeting awareness
            manifest_blueprint = self.create_manifest_blueprint(
                conversation_type, 
                num_messages,
                category=category,
                topic=formatted_topic
            )
            
            # Log whether company targeting is enabled for this conversation
            company_targeting_enabled = manifest_blueprint.get("company_targeting_enabled", False)
            num_companies = len(manifest_blueprint.get("key_companies", []))
            logging.info(f"Conversation {conv_number}: Company targeting {'enabled' if company_targeting_enabled else 'disabled'}, {num_companies} companies included")

            # Generate conversation using the blueprint
            prompt = self.construct_prompt(advisor_name, client_name, conversation_type, num_messages, manifest_blueprint)
            response = await self.call_vertex_ai(prompt)
            
            # Parse the response to get chat lines
            chat_lines = self.parse_response(response, num_messages)
            
            # Create the conversation object with proper ChatLine objects
            conversation = SingleConversation(
                conversation_id=conversation_id,
                timestamp=timestamp,
                category=category,
                topic=formatted_topic,
                lines=chat_lines,  # These are already ChatLine objects
                company_mentions=[]  # Add empty company mentions list
            )

            # [DEBUG] Log conversation details to see what's being created
            logging.info(f"DEBUG: Created conversation object {conversation_id} with {len(chat_lines)} lines, topic: {formatted_topic}")
            
            # Log the manifest
            manifest_log = {
                "conversation_id": conversation_id,
                "type": conversation_type,
                "timestamp": timestamp,
                "category": category,
                "topic": formatted_topic,
                "advisor": advisor_name,
                "client": client_name,
                "num_messages": len(chat_lines),
                "manifest": manifest_blueprint
            }
            
            self.manifest_logger.info(json.dumps(manifest_log))
            
            # [DEBUG] Print details of the conversation to help debugging
            print(f"DEBUG: Generated conversation {conversation_id} for {advisor_name}-{client_name} with {len(chat_lines)} messages")
            
            return conversation
            
        except Exception as e:
            logging.error(f"Error processing conversation {conv_number}: {e}", exc_info=True)
            print(f"DEBUG ERROR: Failed to process conversation {conv_number}: {str(e)}")
            # Return empty conversation on error
            return SingleConversation(
                conversation_id=f"{self.run_id}_{conv_number}_error",
                timestamp=datetime.now().isoformat(),
                category="Error",
                topic="Error",
                lines=[],
                company_mentions=[]  # Add empty company mentions list
            )

    async def generate_synthetic_data(self):
        """
        Generate and save synthetic conversations.
        """
        # Initialize the conversation buffer at the beginning of each generation
        self.conversation_buffer = {}
        print(f"DEBUG: Initialized empty conversation buffer")
        
        tasks = []
        conversation_metadata = []  # Track advisor/client pairs for each conversation
        
        # Create all the conversation generation tasks and track metadata
        for i in range(1, self.num_conversations + 1):
            conversation_type = self.select_conversation_type()
            advisor, client = self.select_advisors_clients()
            num_messages = random.randint(self.min_messages, self.max_messages)
            
            # Store metadata for this conversation
            conversation_metadata.append({
                "index": i,
                "advisor": advisor,
                "client": client,
                "type": conversation_type,
                "messages": num_messages
            })
            
            # Create task
            tasks.append(self.process_conversation(i, conversation_type, advisor, client, num_messages))
        
        # [DEBUG] Log that we're starting to gather results
        print(f"DEBUG: Starting to gather {len(tasks)} conversation generation tasks")
        
        # Wait for all conversation generation to complete
        conversations = await asyncio.gather(*tasks)
        
        # [DEBUG] Log details about the conversations generated
        valid_conversations = [c for c in conversations if c.conversation_id and not c.conversation_id.endswith("_error")]
        print(f"DEBUG: Generated {len(valid_conversations)} valid conversations out of {len(conversations)} total")
        
        # [DEBUG] Check if the buffer already has entries before processing
        print(f"DEBUG: Conversation buffer has {len(self.conversation_buffer)} entries before processing new conversations")
        
        # Add conversations to the buffer using the metadata we tracked
        buffer_additions = 0
        for i, conversation in enumerate(conversations):
            if i < len(conversation_metadata) and conversation.conversation_id and not conversation.conversation_id.endswith("_error"):
                # Get the advisor/client from our metadata
                metadata = conversation_metadata[i]
                advisor = metadata["advisor"]
                client = metadata["client"]
                
                # Create the buffer key
                buffer_key = f"{advisor}_{client}"
                print(f"DEBUG: Processing conversation {i+1} for buffer key '{buffer_key}'")
                
                # Initialize buffer entry if needed
                if buffer_key not in self.conversation_buffer:
                    print(f"DEBUG: Creating new buffer entry for key '{buffer_key}'")
                    self.conversation_buffer[buffer_key] = ConversationFile(
                        version=self.json_version,
                        advisor=advisor,
                        client=client,
                        conversations=[]
                    )
                
                # Add the conversation to the buffer
                self.conversation_buffer[buffer_key].conversations.append(conversation)
                buffer_additions += 1
                print(f"DEBUG: Added conversation {conversation.conversation_id} to buffer with key '{buffer_key}' (buffer now has {len(self.conversation_buffer[buffer_key].conversations)} conversations)")
        
        # [DEBUG] Log each buffer entry and how many conversations it contains
        print(f"DEBUG: Added {buffer_additions} conversations to the buffer across {len(self.conversation_buffer)} entries")
        print(f"DEBUG: Conversation buffer now has {len(self.conversation_buffer)} entries after processing")
        for key, conv_file in self.conversation_buffer.items():
            print(f"DEBUG: Buffer entry '{key}' contains {len(conv_file.conversations)} conversations")
        
        # Save all conversations from the buffer
        for buffer_key, conv_file in self.conversation_buffer.items():
            try:
                # Extract advisor and client from the buffer key
                advisor, client = buffer_key.split("_", 1)
                
                print(f"DEBUG: Saving {len(conv_file.conversations)} conversations for {advisor} and {client}")
                self.save_conversation_file(advisor, client, conv_file)
                print(f"DEBUG: Successfully saved conversations for {advisor} and {client}")
            except Exception as e:
                print(f"DEBUG ERROR: Failed to save conversations for {buffer_key}: {str(e)}")
                logging.error(f"Failed to save conversations for {buffer_key}: {e}")

    async def generate_conversation(
        self,
        advisor_name: str,
        client_name: str,
        conversation_type: str,
        num_messages: int,
        manifest_blueprint: dict,
        max_retries: int = 3
    ) -> SingleConversation:
        for attempt in range(1, max_retries + 1):
            try:
                prompt = self.construct_prompt(advisor_name, client_name, conversation_type, num_messages, manifest_blueprint)
                logging.debug(f"Constructed Prompt for Conversation: {prompt}")
                raw_response = await self.call_vertex_ai(prompt)
                logging.debug(f"Raw LLM Response for Conversation: {raw_response}")
                if not raw_response:
                    logging.error("Received empty response from LLM.")
                    continue
                lines = self.parse_response(raw_response, num_messages)
                if not lines:
                    logging.warning(f"Attempt {attempt}: Parsed conversation lines are empty.")
                    continue
                return SingleConversation(
                    conversation_id="",
                    timestamp="",
                    category=conversation_type,
                    topic=conversation_type,
                    lines=lines,
                    company_mentions=[]  # Add empty company mentions list
                )
            except Exception as e:
                logging.error(f"Error generating conversation on attempt {attempt}: {e}", exc_info=True)
        logging.error(f"Failed to generate a valid conversation after {max_retries} attempts.")
        return SingleConversation(
            conversation_id="",
            timestamp="",
            category=conversation_type,
            topic=conversation_type,
            lines=[],
            company_mentions=[]  # Add empty company mentions list
        )

    def load_few_shot_examples(self, conversation_type: str, script: Dict = None) -> str:
        """
        Loads few-shot examples from files, generates them if missing.
        """
        examples_file = self.few_shot_examples_dir / f"{sanitize_filename(conversation_type)}.txt"
        if examples_file.exists():
            logging.info(f"Loading few-shot examples from: {examples_file}")
            try:
                with open(examples_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logging.warning(f"Error reading examples file: {examples_file}: {e}.")
                return ""
        else:
            logging.info(f"No few-shot examples found for {conversation_type}. Generating...")
            if script:
                examples = self.generate_few_shot_examples(conversation_type, script)
                try:
                    with open(examples_file, 'w', encoding='utf-8') as f:
                        f.write(examples)
                    logging.info(f"Generated and saved few-shot examples to: {examples_file}")
                    return examples
                except Exception as e:
                    logging.error(f"Error saving generated examples to file: {e}")
                    return ""
            else:
                logging.warning(f"No script provided for generating few-shot examples for {conversation_type}.")
                return ""

    def generate_few_shot_examples(self, conversation_type: str, script: Dict) -> str:
        """
        Generates few-shot examples using the LLM.
        """
        prompt = self.construct_few_shot_generation_prompt(conversation_type, script)
        try:
            examples = asyncio.run(self.call_vertex_ai(prompt))
            logging.info(f"Generated few-shot examples: {examples}")
            return examples
        except Exception as e:
            logging.error(f"Error generating few-shot examples: {e}")
            return ""

    def construct_few_shot_generation_prompt(self, conversation_type: str, script: Dict) -> str:
        prompt = f"""
        Generate 3-5 diverse and realistic conversation examples for the following scenario:

        Conversation Type: {conversation_type}

        Primary Topic: {script.get("primary_topic")}

        Key Companies: {', '.join(script.get("key_companies", []))}

        Conversation Flow:
        """
        for turn in script.get("conversation_flow", []):
            prompt += f"\n- Speaker: {turn['speaker']}, Topic: {turn['topic']}"
        prompt += """

        The examples should adhere to the following guidelines:

        - Use a professional and engaging tone.
        - Incorporate relevant company mentions naturally.
        - Vary message lengths and styles.
        - Follow the conversation flow provided.
        - Format each example as a JSON array within <BEGIN CONVERSATION> and <END CONVERSATION> tags, with each message having "speaker" and "text" keys.

        <BEGIN CONVERSATION>
        [
            {
                "speaker": "0",
                "text": "Example text..."
            },
            {
                "speaker": "1",
                "text": "Example text..."
            }
        ]
        <END CONVERSATION>

        Provide only the JSON examples within the tags.
        """
        return prompt

    def get_message_length_guidance(self, num_messages: int) -> List[str]:
        ratio = self.message_length_ratio
        num_short = int(num_messages * ratio["short"])
        num_long = int(num_messages * ratio["long"])
        num_medium = num_messages - num_short - num_long
        length_guidance = (["short"] * num_short + ["medium"] * num_medium + ["long"] * num_long)
        random.shuffle(length_guidance)
        logging.debug(f"Message length guidance: {length_guidance}")
        return length_guidance

    def setup_output_directory(self) -> Path:
        """Sets up the output directory with run_id as parent."""
        try:
            # run_output_dir = self.output_dir_base / self.run_id
            # run_output_dir.mkdir(parents=True, exist_ok=True)
            run_output_dir = self.output_dir_base / self.run_id
            run_output_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Output directory set to: {run_output_dir}")
        except Exception as e:
            logging.error(f"Error setting up output directory: {e}")
            raise
        return run_output_dir

    def initialize_vertex_ai(self):
        service_account_json_path = "./google-service-account.json"
        logging.info(f"Attempting to initialize Vertex AI with hardcoded key file: {service_account_json_path}")
        try:
            credentials_path = service_account_json_path
            if not os.path.exists(credentials_path):
                logging.error(f"Hardcoded Service Account key file NOT FOUND at: {credentials_path}")
                raise FileNotFoundError(f"Service Account key file not found at: {credentials_path}")
            import google.auth
            credentials, project_id_from_file = google.auth.load_credentials_from_file(credentials_path)
            logging.info(f"Successfully loaded credentials from hardcoded path.")
            vertexai.init(project=self.project_id, location=self.location, credentials=credentials)
            logging.info(f"Vertex AI initialized with project: {self.project_id}, location: {self.location}, using hardcoded credentials.")
            self.llm = GenerativeModel(model_name=self.model_name)
            logging.info(f"Initialized GenerativeModel with model name '{self.model_name}'.")
        except Exception as e:
            logging.error(f"Error initializing Vertex AI with hardcoded credentials: {e}")
            raise

    def save_conversation_file(self, advisor: str, client: str, conversation_file: ConversationFile):
        sanitized_advisor = sanitize_filename(advisor)
        sanitized_client = sanitize_filename(client)
        advisor_dir = self.output_dir / sanitized_advisor
        filename = f"{sanitized_client}.json"
        filepath = advisor_dir / filename
        try:
            advisor_dir.mkdir(parents=True, exist_ok=True)
            logging.debug(f"Ensured advisor directory exists: {advisor_dir}")
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                existing_data['conversations'].extend([conv.to_dict() for conv in conversation_file.conversations])
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=4)
                logging.info(f"Appended conversations to existing file {filepath}")
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(conversation_file.to_dict(), f, indent=4)
                logging.info(f"Created new conversation file at {filepath}")
        except Exception as e:
            logging.error(f"Error saving conversation file to {filepath}: {e}")


def main():
    try:
        args = parse_arguments()  # Parse command-line arguments
        logging.info(f"Using run_id: {args.run_id}")
        generator = SyntheticChatGenerator(config, run_id=args.run_id)
        asyncio.run(generator.generate_synthetic_data())
        logging.info("Synthetic chat data generation completed successfully.")
    except Exception as e:
        logging.critical(f"Critical error in synthetic chat data generation: {e}")

if __name__ == "__main__":
    main()
