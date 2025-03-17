
import os
import json
import random
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import uuid
from datetime import datetime

import google
import asyncio
from google.cloud import aiplatform # might be outdated package import INSPECT
#import aiplatform

import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from vertexai.preview.language_models import ChatSession

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
    category: str
    topic: str
    lines: List[ChatLine] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "topic": self.topic,
            "lines": [line.__dict__ for line in self.lines]
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



class SyntheticChatGenerator:
    def __init__(self, config):
        self.personas = config.PERSONAS # NEW
        self.company_list = config.COMPANY_LIST # NEW
        self.conversation_types = config.CONVERSATION_TYPES # NEW
        self.message_formats = config.MESSAGE_FORMATS # NEW
        self.ticker_symbols = config.TICKER_SYMBOLS # NEW
        self.common_abbreviations = config.COMMON_ABBREVIATIONS # NEW
        self.misspellings = config.MISSPELLINGS # NEW
        self.formal_names = config.FORMAL_NAMES # NEW
        self.message_length_ratio = config.MESSAGE_LENGTH_RATIO # Load length ratio config
        self.few_shot_examples_dir = Path(config.FEW_SHOT_EXAMPLES_DIR) # Path to examples dir

        self.temperature = config.TEMPERATURE
        self.top_p = config.TOP_P
        self.top_k = config.TOP_K

        self.project_id = config.PROJECT_ID
        self.location = config.LOCATION
        self.model_name = config.MODEL_NAME.lower()
        self.taxonomy_file = config.TAXONOMY_FILE
        self.advisor_names = config.ADVISOR_NAMES  
        self.client_names = config.CLIENT_NAMES      
        #self.output_dir = Path(config.OUTPUT_DIR)
        self.json_version = config.JSON_VERSION
        self.num_conversations = config.NUM_CONVERSATIONS
        self.min_messages = config.MIN_MESSAGES
        self.max_messages = config.MAX_MESSAGES
        self.topic_distribution = config.TOPIC_DISTRIBUTION

        self.taxonomy = self.load_taxonomy()
        self.flattened_topics = self.flatten_taxonomy(self.taxonomy)
        self.conversation_type_metadata = self.taxonomy.get("conversation_types", {})

        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6] # Generate run_id
        self.output_dir = self.setup_output_directory() # Setup output dir with run_id
        #self.setup_output_directory()
        self.initialize_vertex_ai()
        self.conversation_buffer = {}

        logging.info("--- Credential Verification Logging ---")

    def load_taxonomy(self) -> Dict[str, Any]:
        # We might not use taxonomy.json anymore, but let's keep this function for now,
        # or you could adapt it to load company-related data if needed from a file.
        try:
            with open(self.taxonomy_file, 'r') as f:
                taxonomy = json.load(f)
                logging.info(f"Loaded taxonomy from {self.taxonomy_file}.")
                return taxonomy
        except Exception as e:
            logging.error(f"Error loading taxonomy file: {e}")
            raise

    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str]]:
        # This function might also become less relevant if we don't use taxonomy.json.
        # Keep it for now, or adapt if you decide to use a company taxonomy file later.
        flattened = []
        for category, subcats in taxonomy.items():
            if isinstance(subcats, dict):
                for subcategory, topics in subcats.items():
                    for topic in topics:
                        combined_category = f"{category} - {subcategory}"
                        flattened.append((combined_category, topic))
            elif isinstance(subcats, list):
                for topic in subcats:
                    flattened.append((category, topic))
            else:
                logging.warning(f"Unexpected taxonomy structure for category '{category}'.")
        logging.info(f"Flattened taxonomy into {len(flattened)} topics.")
        return flattened


    def load_few_shot_examples(self, conversation_type: str) -> str:
        """
        Loads few-shot examples from files, with fallback to generic examples.
        """
        examples_file = self.few_shot_examples_dir / f"{sanitize_filename(conversation_type)}.txt" # Type-specific file
        generic_examples_file = self.few_shot_examples_dir / "generic.txt" # Generic fallback

        if examples_file.exists():
            logging.info(f"Loading few-shot examples from: {examples_file}")
            try:
                with open(examples_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logging.warning(f"Error reading examples file: {examples_file}: {e}. Falling back to generic examples.")
                pass # Fallback to generic if type-specific file has issues

        logging.info(f"Falling back to generic few-shot examples from: {generic_examples_file}") # Log fallback
        try:
            with open(generic_examples_file, 'r', encoding='utf-8') as f: # Load generic examples
                return f.read()
        except FileNotFoundError:
            logging.warning(f"Generic examples file not found: {generic_examples_file}. No few-shot examples will be used.")
            return "" # No examples available
        except Exception as e:
            logging.error(f"Error reading generic examples file: {generic_examples_file}: {e}")
            return "" # Error reading generic - return empty string


    def get_message_length_guidance(self, num_messages: int) -> List[str]:
        """
        Determines message length guidance based on MESSAGE_LENGTH_RATIO.
        Returns a list of length types ("short", "medium", "long") for each message.
        """
        ratio = self.message_length_ratio
        num_short = int(num_messages * ratio["short"])
        num_long = int(num_messages * ratio["long"])
        num_medium = num_messages - num_short - num_long # Ensure total messages matches

        length_guidance = (
            ["short"] * num_short + ["medium"] * num_medium + ["long"] * num_long
        )
        random.shuffle(length_guidance) # Shuffle to distribute lengths randomly
        logging.debug(f"Message length guidance: {length_guidance}")
        return length_guidance

    # def setup_output_directory(self):
    #     try:
    #         self.output_dir.mkdir(parents=True, exist_ok=True)
    #         logging.info(f"Output directory set up at {self.output_dir}")
    #     except Exception as e:
    #         logging.error(f"Error setting up output directory: {e}")
    #         raise

    def setup_output_directory(self) -> Path:
        """Sets up the output directory with run_id as parent."""
        try:
            run_output_dir = self.output_dir_base / self.run_id # Create run-specific directory
            run_output_dir.mkdir(parents=True, exist_ok=True) # Create run dir if it doesn't exist
            logging.info(f"Output directory set to: {run_output_dir}")
        except Exception as e:
            logging.error(f"Error setting up output directory: {e}")
            raise
        return run_output_dir # Return the run-specific output directory

    def initialize_vertex_ai(self):
        service_account_json_path = "./google-service-account.json"

        logging.info(f"Attempting to initialize Vertex AI with hardcoded key file: {service_account_json_path}")
        try:
            # Explicitly load credentials from the hardcoded file path
            credentials_path = service_account_json_path # Use the hardcoded path
            if not os.path.exists(credentials_path):
                logging.error(f"Hardcoded Service Account key file NOT FOUND at: {credentials_path}")
                raise FileNotFoundError(f"Service Account key file not found at: {credentials_path}")


            # Load credentials using google.auth.load_credentials_from_file
            import google.auth
            credentials, project_id_from_file = google.auth.load_credentials_from_file(credentials_path)

            logging.info(f"Successfully loaded credentials from hardcoded path.")
            vertexai.init(project=self.project_id, location=self.location, credentials=credentials) # Initialize with explicit credentials
            logging.info(f"Vertex AI initialized with project: {self.project_id}, location: {self.location}, using hardcoded credentials.")
            #GenerativeModel(MODEL_NAME)
            self.llm = GenerativeModel(model_name=self.model_name)
            logging.info(f"Initialized GenerativeModel with model name '{self.model_name}'.")

        except Exception as e:
            logging.error(f"Error initializing Vertex AI with hardcoded credentials: {e}")
            raise

    # --- NEW FUNCTION TO SELECT CONVERSATION TYPE ---
    def select_conversation_type(self) -> str:
        conversation_type = random.choice(self.conversation_types)
        logging.debug(f"Selected conversation type: {conversation_type}")
        return conversation_type

    # --- NEW FUNCTION TO GET MESSAGE FORMAT ---
    def get_message_format(self, conversation_type: str) -> str:
        message_format = self.message_formats.get(conversation_type, "formal") # Default to formal if not found
        logging.debug(f"Message format for {conversation_type}: {message_format}")
        return message_format

    # --- NEW FUNCTION TO SELECT PERSONA ---
    def select_persona(self) -> str:
        persona = random.choice(self.personas)
        logging.debug(f"Selected persona: {persona}")
        return persona
    
    def select_advisors_clients(self) -> Tuple[str, str]:
        advisor = random.choice(self.advisor_names)
        client = random.choice(self.client_names)
        logging.debug(f"Selected advisor-client pair: {advisor} - {client}")
        return advisor, client

    def assign_random_attributes(self) -> Tuple[int, str]:
        """
        Assign random age and communication style to advisors and clients for variability.
        Returns a tuple of (age, communication_style).
        """
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

    async def call_vertex_ai(self, prompt: str) -> str:
        try:
            generation_config = GenerationConfig(
                max_output_tokens=1200,
                temperature=self.temperature, #.2
                top_p=self.top_p, #1
                top_k=self.top_k # 32
            )
            response = await self.llm.generate_content_async(
                contents=[prompt],
                generation_config=generation_config,
                stream=False
            )
            # Extract raw response text
            raw_response = response.candidates[0].content.text.strip()
            logging.info(f"Raw LLM Response: {raw_response}")
            return raw_response
        except Exception as e:
            logging.error(f"Error calling Vertex AI: {e}", exc_info=True)
            return ""

    # --- NEW FUNCTION TO SELECT COMPANY NAME VARIATIONS ---
    def get_company_name_variations(self) -> Dict[str, List[str]]:
        company_variations = {}
        for company in self.company_list:
            variations = [company] # Start with formal name
            ticker_match = [ticker for ticker in self.ticker_symbols if ticker.lower() in company.lower()]
            if ticker_match:
                variations.append(ticker_match[0]) # Add ticker if available

            abbreviation_match = [abbr for abbr in self.common_abbreviations if abbr.lower() in company.lower()]
            if abbreviation_match:
                variations.append(abbreviation_match[0]) # Add abbreviation if available

            misspelling = random.choice(self.misspellings) if self.misspellings else None #Random misspelling from list - this is basic. could be improved.
            if misspelling:
                 variations.append(misspelling.replace("stanly", company.split(" ")[-1].lower())) # Simple replace to make misspelling company relevant


            company_variations[company] = list(set(variations)) # Use set to remove duplicates and convert back to list
        return company_variations


    def select_topic(self) -> Tuple[str, str]: # We might not use this function in the same way now.
        # Keeping it for now to avoid breaking things, but we'll use select_conversation_type instead.
        if self.topic_distribution == "uniform":
            category, topic = random.choice(self.flattened_topics) # Still choosing from taxonomy, might remove later
            logging.debug(f"Selected topic (uniform): {category} - {topic}")
            return category, topic
        else:
            # Implement custom distribution logic if needed
            category, topic = random.choice(self.flattened_topics) # Still choosing from taxonomy, might remove later
            logging.debug(f"Selected topic (default): {category} - {topic}")
            return category, topic

    def construct_prompt(
        self,
        advisor_name: str,
        client_name: str,
        conversation_type: str,
        num_messages: int
    ) -> str:
        """
        Constructs prompt with dynamic few-shot examples and length guidance.
        """
        # ... (Persona and company variation selection - remains same) ...
        message_format = self.get_message_format(conversation_type)
        conversation_metadata = self.conversation_type_metadata.get(conversation_type, {}) # Not really using metadata yet in this version.
        message_style = conversation_metadata.get("message_style", "professional") # Not really using message_style yet in this version.

        # Get company name variations and example companies prompt (same as before)
        company_name_variations = self.get_company_name_variations()
        example_companies_prompt = ""
        company_example_count = 3
        example_companies = random.sample(self.company_list, company_example_count)
        for company in example_companies:
            variations_str = ", ".join(company_name_variations[company])
            example_companies_prompt += f"- **{company}**: Variations like: {variations_str}\n"

        # Load few-shot examples dynamically
        few_shot_examples = self.load_few_shot_examples(conversation_type)

        # Get message length guidance
        message_length_guidance = self.get_message_length_guidance(num_messages) # Get length types for each message

        # ============================================
        # REVISED MAIN PROMPT - WITH DYNAMIC EXAMPLES AND LENGTH GUIDANCE
        # ============================================
        prompt = (
            f"Generate a realistic and {message_format} chat conversation focused on **{conversation_type}** between two financial professionals on Symphony. "
            f"The primary goal is company mentions for tagging, with varied message lengths.\n\n"
            f"Financial Professional 1 (Advisor): {advisor_name}, Persona: {self.select_persona()}\n" # Persona selection in prompt
            f"Financial Professional 2 (Client): {client_name}, Persona: {self.select_persona()}\n\n" # Persona selection in prompt
            f"Conversation Topic: {conversation_type}\n"
            f"Message Format: {message_format}\n\n"

            f"**Company Mention Guidelines:**\n"
            f"- MUST heavily feature company mentions from the provided list, using varied formats (formal, abbreviations, tickers, misspellings).\n"
            f"- Example Company Variations:\n{example_companies_prompt}"
            f"- Company List Examples (see config.COMPANY_LIST):\n  - ...and more.\n"
            f"- Ticker Examples: {', '.join(self.ticker_symbols)}\n"
            f"- Abbreviation Examples: {', '.join(self.common_abbreviations)}\n"
            f"- Misspelling Examples: {', '.join(self.misspellings)}\n\n"

            f"**Message Length and Style Guidelines:**\n"
            f"1. Generate a conversation with **exactly {num_messages} messages**, with message lengths guided as follows:\n" # Explicit message count
            f"   - **Message Length Distribution:** [ {', '.join(message_length_guidance)} ] (This is guidance, try to approximate).\n" # Show length guidance in prompt
            f"   - **Short Messages:** A few words.\n"
            f"   - **Medium Messages:** A sentence or two providing some context or detail.\n"
            f"   - **Long Messages:** Multi-sentence messages, like market updates or stock analysis excerpts.\n"
            f"2. Maintain a {message_format} and professional tone.\n"
            f"3. Be concise and professional.\n"
            f"4. Focus on realistic financial discussions.\n"
            f"5. Integrate multiple company mentions within messages naturally.\n\n"

            f"**Conversation Flow Guidelines:**\n"
            f"7. Conversation initiation can be by either professional.\n"
            f"8. Speakers should alternate naturally.\n"
            f"9. Conversation should have a logical flow and progression, with each message relating to the previous ones.\n\n"

            f"**Instructions for Output Format:**\n"
            f"- **Output Format:** Structure the conversation as a JSON array enclosed within `<BEGIN CONVERSATION>` and `<END CONVERSATION>` tags.\n"
            f"- **Message Object Structure:** Each message in the JSON array must be a JSON object with exactly two keys: 'speaker' (value '0' or '1') and 'text' (string value).\n"
            f"- **No Extraneous Content:**  Do not include any text outside of the JSON array within the tags.  No introductory or concluding sentences, just the JSON.\n"
            f"- **JSON Validity:** Ensure the output is valid, well-formed JSON and easily parsable.\n"
            f"- **Text Sanitization:**  Ensure all text content within the JSON is properly formatted for JSON (escape special characters if needed).\n\n"

            f"**Few-Shot Examples (for {conversation_type} - Style and Format):**\n" #Dynamic examples section
            f"{few_shot_examples}\n\n" # Insert loaded few-shot examples

            f"<BEGIN CONVERSATION>\n[\n  {{\n    \"speaker\": \"0\" or \"1\",\n    \"text\": \"...\"\n  }},\n  ... (messages)\n]\n<END CONVERSATION>\n\n"
            f"**IMPORTANT: Output valid JSON array within <BEGIN CONVERSATION> and <END CONVERSATION> tags ONLY.**"
        )
        logging.debug(f"Constructed Prompt: {prompt}")
        return prompt

    def parse_response(self, response: str, expected_messages: int) -> List[ChatLine]:
        try:
            start_tag = "<BEGIN CONVERSATION>"
            end_tag = "<END CONVERSATION>"
            
            start = response.find(start_tag)
            end = response.find(end_tag)
            
            if start == -1 or end == -1:
                logging.error("Missing conversation tags in the LLM response.")
                logging.debug(f"Full LLM Response: {response}")
                return []
            
            json_str = response[start + len(start_tag):end].strip()
            
            if not json_str.startswith("[") or not json_str.endswith("]"):
                logging.error("JSON array not found within conversation tags.")
                logging.debug(f"Extracted JSON string: {json_str}")
                return []
            
            # Sanitize the JSON string by escaping backslashes and quotes
            # Alternatively, use more sophisticated sanitization if needed
            json_str = json_str.encode('utf-8', 'ignore').decode('utf-8')
            data = json.loads(json_str)
            
            if not isinstance(data, list):
                logging.error("Parsed JSON is not a list.")
                logging.debug(f"Parsed JSON data: {data}")
                return []
            
            lines = []
            for index, line in enumerate(data):
                if not isinstance(line, dict):
                    logging.error(f"Message at index {index} is not a dictionary.")
                    continue
                if "speaker" not in line or "text" not in line:
                    logging.error(f"Message at index {index} missing 'speaker' or 'text' keys.")
                    continue
                # Further sanitize text fields
                text = line["text"].encode('utf-8', 'ignore').decode('utf-8')
                lines.append(ChatLine(speaker=line["speaker"], text=text))
            
            if len(lines) != expected_messages:
                logging.warning(f"Expected {expected_messages} messages, but got {len(lines)}.")
            
            return lines
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error: {e}")
            logging.debug(f"Malformed JSON: {response}")
            return []
        except Exception as e:
            logging.error(f"Error parsing response: {e}")
            logging.debug(f"Response content: {response}")
            return []

    async def generate_conversation(
        self,
        advisor_name: str,
        client_name: str,
        conversation_type: str, # Changed from category/topic to conversation_type
        num_messages: int,
        max_retries: int = 3
    ) -> SingleConversation:
        """
        Generates a single company tagging conversation.
        """
        for attempt in range(1, max_retries + 1):
            try:
                prompt = self.construct_prompt(advisor_name, client_name, conversation_type, num_messages) # Changed args
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

                # Create and return a SingleConversation instance
                return SingleConversation(
                    conversation_id="",
                    timestamp="",
                    category=conversation_type, # Using conversation_type as category now
                    topic=conversation_type, # And topic
                    lines=lines
                )

            except Exception as e:
                logging.error(f"Error generating conversation on attempt {attempt}: {e}", exc_info=True)

        logging.error(f"Failed to generate a valid conversation after {max_retries} attempts.")
        return SingleConversation(
            conversation_id="",
            timestamp="",
            category=conversation_type, # Using conversation_type as category now
            topic=conversation_type, # And topic
            lines=[]
        )

    # def sanitize_text(self, text: str) -> str:
    #     """
    #     Sanitizes text to remove or replace unwanted characters.
    #     Currently removes unicode en dashes (u2013) and can be extended.
    #     """
    #     # Remove unicode en dash (\u2013) - you can add more regex replacements here
    #     text = re.sub(r'\u2013', '-', text) # Replace en dash with hyphen
    #     return text

    async def process_conversation(
        self,
        conv_number: int,
        conversation_type: str, # Changed from category/topic to conversation_type
        advisor_name: str,
        client_name: str,
        num_messages: int
    ):
        """
        Processes and buffers a single company tagging conversation.
        """
        try:
            # Log advisor and client names
            logging.debug(f"Processing Conversation {conv_number}: Advisor - {advisor_name}, Client - {client_name}")

            # Generate the conversation
            single_conv = await self.generate_conversation(advisor_name, client_name, conversation_type, num_messages) # Changed args

            if not single_conv.lines:
                logging.warning(f"Conversation {conv_number} between {advisor_name} and {client_name} has no messages. Skipping.")
                return

            # Generate unique conversation ID and timestamp
            conv_id = f"conv_{conv_number:04d}"
            timestamp = datetime.utcnow().isoformat() + "Z"

            # Update single_conv with ID and timestamp
            single_conv.conversation_id = conv_id
            single_conv.timestamp = timestamp

            # Buffer the conversation
            key = (advisor_name, client_name)
            if key not in self.conversation_buffer:
                self.conversation_buffer[key] = ConversationFile(
                    version=self.json_version,
                    advisor=advisor_name,
                    client=client_name,
                    conversations=[]
                )
            self.conversation_buffer[key].conversations.append(single_conv)

            logging.info(f"Generated conversation {conv_number}/{self.num_conversations} between {advisor_name} and {client_name}")

        except Exception as e:
            logging.error(f"Failed to process conversation {conv_number}: {e}", exc_info=True)


    async def generate_synthetic_data(self):
        tasks = []
        for i in range(1, self.num_conversations + 1):
            conversation_type = self.select_conversation_type() # Select conversation_type now instead of topic/category
            advisor, client = self.select_advisors_clients()
            num_messages = random.randint(self.min_messages, self.max_messages)
            tasks.append(self.process_conversation(i, conversation_type, advisor, client, num_messages)) # Changed args

        # Execute all tasks concurrently
        await asyncio.gather(*tasks)

        for (advisor, client), conv_file in self.conversation_buffer.items():
            try:
                self.save_conversation_file(advisor, client, conv_file)
            except Exception as e:
                logging.error(f"Failed to save conversations for {advisor} and {client}: {e}")

    # def save_conversation_file(self, advisor: str, client: str, conversation_file: ConversationFile):
    #     """
    #     Saves the conversation file as a JSON file in the specified output directory.

    #     Parameters:
    #     - advisor (str): The name of the advisor.
    #     - client (str): The name of the client.
    #     - conversation_file (ConversationFile): The conversation file data.
    #     """
    #     sanitized_advisor = sanitize_filename(advisor)
    #     sanitized_client = sanitize_filename(client)

    #     advisor_dir = self.output_dir / sanitized_advisor
    #     filename = f"{sanitized_client}.json"  # Single file per advisor-client pair
    #     filepath = advisor_dir / filename
    #     try:
    #         advisor_dir.mkdir(parents=True, exist_ok=True)
    #         logging.debug(f"Ensured advisor directory exists: {advisor_dir}")

    #         if filepath.exists():
    #             with open(filepath, 'r', encoding='utf-8') as f:
    #                 existing_data = json.loadtemf)
    #             existing_data['conversations'].extend([conv.to_dict() for conv in conversation_file.conversations])
    #             with open(filepath, 'w', encoding='utf-8') as f:
    #                 json.dump(existing_data, f, indent=4)
    #             logging.info(f"Appended conversations to existing file {filepath}")
    #         else:
    #             with open(filepath, 'w', encoding='utf-8') as f:
    #                 json.dump(conversation_file.to_dict(), f, indent=4)
    #             logging.info(f"Created new conversation file at {filepath}")
    #     except Exception as e:
    #         logging.error(f"Error saving conversation file to {filepath}: {e}")

    def save_conversation_file(self, advisor: str, client: str, conversation_file: ConversationFile):
        """
        Saves the conversation file as a JSON file in the specified run-specific output directory.

        Parameters:
        - advisor (str): The name of the advisor.
        - client (str): The name of the client.
        - conversation_file (ConversationFile): The conversation file data.
        """
        sanitized_advisor = sanitize_filename(advisor)
        sanitized_client = sanitize_filename(client)

        advisor_dir = self.output_dir / sanitized_advisor # Advisor dir under run_id dir
        filename = f"{sanitized_client}.json"  # Single file per advisor-client pair
        filepath = advisor_dir / filename
        try:
            advisor_dir.mkdir(parents=True, exist_ok=True) # Ensure advisor dir in run dir exists
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
        generator = SyntheticChatGenerator(config)
        asyncio.run(generator.generate_synthetic_data())
        logging.info("Synthetic chat data generation completed successfully.")
    except Exception as e:
        logging.critical(f"Critical error in synthetic chat data generation: {e}")

if __name__ == "__main__":
    main()


