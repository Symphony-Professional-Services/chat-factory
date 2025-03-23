
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

        self.conversation_types = config.CONVERSATION_TYPES # NEW
        self.message_formats = config.MESSAGE_FORMATS # NEW
        self.message_length_ratio = config.MESSAGE_LENGTH_RATIO # Load length ratio config
        self.few_shot_examples_dir = Path(config.FEW_SHOT_EXAMPLES_DIR) # Path to examples dir
        self.company_data_file = config.COMPANY_DATA_FILE  # Path to CSV file


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
        self.output_dir_base = Path(config.OUTPUT_DIR)  # Initialize output_dir_base

        self.output_dir = self.setup_output_directory() # Setup output dir with run_id
        self.setup_output_directory()
        self.initialize_vertex_ai()
        self.conversation_buffer = {}

        self.company_data = self.load_company_data()  # Load company data from CSV
        logging.info("--- Credential Verification Logging ---")

        # **** New: Use a single directory for both conversation scripts and manifests ****
        self.conversation_manifest_dir = Path(config.CONVERSATION_MANIFEST_DIR)
        self.conversation_manifest_dir.mkdir(parents=True, exist_ok=True)

        # Create a dedicated logger for conversation manifests
        self.manifest_logger = logging.getLogger("conversation_manifest")
        self.manifest_logger.setLevel(logging.INFO)
        if not self.manifest_logger.handlers:
            manifest_log_file = self.conversation_manifest_dir / "conversation_manifest.log"
            fh = logging.FileHandler(manifest_log_file)
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.manifest_logger.addHandler(fh)

    def load_company_data(self) -> List[Dict]:
        """Loads company data from the CSV file."""
        company_data: List[Dict] = [] # Initialize company_data as an empty list
        try:
            with open(self.company_data_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Split comma-separated strings into lists
                    row['variations'] = [v.strip() for v in row.get('variations', '').split(',') if v.strip()]
                    row['abbreviations'] = [abbr.strip() for abbr in row.get('abbreviations', '').split(',') if abbr.strip()]
                    row['misspellings'] = [misspelling.strip() for misspelling in row.get('misspellings', '').split(',') if misspelling.strip()]
                    company_data.append(row)
            logging.info(f"Loaded {len(company_data)} companies from {self.company_data_file}")
        except FileNotFoundError:
            logging.error(f"Company data file not found: {self.company_data_file}")
            raise
        except Exception as e:
            logging.error(f"Error loading company data: {e}")
            raise
        return company_data

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
                return ""  # Return empty string on error
        else:
            logging.info(f"No few-shot examples found for {conversation_type}. Generating...")
            if script:
                examples = self.generate_few_shot_examples(conversation_type, script)
                # Save generated examples to the file
                try:
                    with open(examples_file, 'w', encoding='utf-8') as f:
                        f.write(examples)
                    logging.info(f"Generated and saved few-shot examples to: {examples_file}")
                    return examples
                except Exception as e:
                    logging.error(f"Error saving generated examples to file: {e}")
                    return ""  # Return empty string on error
            else:
                logging.warning(
                    f"No script provided for generating few-shot examples for {conversation_type}.")
                return ""  # Return empty string if no script



    def generate_few_shot_examples(self, conversation_type: str, script: Dict) -> str:
        """
        Generates few-shot examples using the LLM.
        """
        prompt = self.construct_few_shot_generation_prompt(conversation_type, script)
        try:
            examples = asyncio.run(self.call_vertex_ai(prompt))  # Assuming call_vertex_ai is async
            logging.info(f"Generated few-shot examples: {examples}")
            return examples
        except Exception as e:
            logging.error(f"Error generating few-shot examples: {e}")
            return ""

    def construct_few_shot_generation_prompt(self, conversation_type: str, script: Dict) -> str:
        """
        Constructs the prompt for generating few-shot examples.
        """
        # --- Example Script Structure ---
        # {
        #     "conversation_type": "Earnings Discussion",
        #     "primary_topic": "Q2 2024 Tech Earnings",
        #     "key_companies": ["MSFT", "AAPL", "GOOGL"],
        #     "conversation_length": "medium",
        #     "persona_advisor": "Analytical",
        #     "persona_client": "Inquisitive",
        #     "conversation_flow": [
        #         {
        #             "speaker": "advisor",
        #             "topic": "Initial market overview"
        #         },
        #         {
        #             "speaker": "client",
        #             "topic": "Questions about specific companies"
        #         },
        #         {
        #             "speaker": "advisor",
        #             "topic": "Analysis of MSFT earnings"
        #         },
        #         {
        #             "speaker": "client",
        #             "topic": "Comparison of AAPL and GOOGL"
        #         }
        #     ]
        # }

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

        -  Use a professional and engaging tone.
        -  Incorporate relevant company mentions naturally.
        -  Vary message lengths and styles.
        -  Follow the conversation flow provided.
        -  Format each example as a JSON array within <BEGIN CONVERSATION> and <END CONVERSATION> tags, with each message having "speaker" and "text" keys, as shown below:

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
        message_format = self.get_message_format(conversation_type)
        conversation_metadata = self.conversation_type_metadata.get(conversation_type, {})
        message_style = conversation_metadata.get("message_style", "professional")

        # Get company name variations and example companies prompt
        company_name_variations = self.get_company_name_variations()
        example_companies_prompt = ""
        company_example_count = 3
        example_companies = random.sample(self.company_data, company_example_count)
        for company_dict in example_companies:
            company = company_dict['name']
            variations = [company]
            if company_dict.get('variations'):
                # Directly extend the list; no need to call .split(',')
                variations.extend(company_dict['variations'])
            if company_dict.get('abbreviations'):
                variations.extend(company_dict['abbreviations'])
            ticker = company_dict.get('ticker')
            if ticker:
                variations.append(ticker)
            example_companies_prompt += f"- **{company}**: Variations like: {', '.join(set(variations))}\n"

        # Load few-shot examples dynamically
        few_shot_examples = self.load_few_shot_examples(conversation_type)

        # Get message length guidance
        message_length_guidance = self.get_message_length_guidance(num_messages)

        prompt = (
            f"Generate a realistic and {message_format} chat conversation focused on **{conversation_type}** between two financial professionals on Symphony. "
            f"The primary goal is company mentions for tagging, with varied message lengths.\n\n"
            f"Financial Professional 1 (Advisor): {advisor_name}, Persona: {self.select_persona()}\n"
            f"Financial Professional 2 (Client): {client_name}, Persona: {self.select_persona()}\n\n"
            f"Conversation Topic: {conversation_type}\n"
            f"Message Format: {message_format}\n\n"
            f"**Company Mention Guidelines:**\n"
            f"- MUST heavily feature company mentions from the provided list, using varied formats (formal, abbreviations, tickers, misspellings).\n"
            f"- Example Company Variations:\n{example_companies_prompt}"
            f"- Company List Examples (see config.COMPANY_DATA_FILE):\n"
        )
        for i in range(min(5, len(self.company_data))):
            prompt += f"  - {self.company_data[i]['name']} ({self.company_data[i].get('ticker', '')})\n"
        prompt += (
            f"- ...and more.\n"
            f"- Ticker Examples (from COMPANY_DATA_FILE): {', '.join(set(c['ticker'] for c in self.company_data if c.get('ticker')))}\n"
            f"- Abbreviation Examples (from COMPANY_DATA_FILE): {', '.join(set(abbr for c in self.company_data if c.get('abbreviations') for abbr in c['abbreviations']))}\n"
            f"- Misspelling Examples (from COMPANY_DATA_FILE): {', '.join(set(misspelling for c in self.company_data if c.get('misspellings') for misspelling in c['misspellings']))}\n\n"
            f"**Message Length and Style Guidelines:**\n"
            f"1. Generate a conversation with **exactly {num_messages} messages**, with message lengths guided as follows:\n"
            f"   - **Message Length Distribution:** [ {', '.join(message_length_guidance)} ] (This is guidance, try to approximate).\n"
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
            f"**Instructions for Output Format - VERY IMPORTANT!**\n"
            f"- **Output Format:** Structure the ENTIRE conversation as a **single JSON array** enclosed within the **EXACT** tags: `<BEGIN CONVERSATION>` and `<END CONVERSATION>`. Do not include any other text outside these tags.\n"
            f"- **Message Object Structure:** Each message in the JSON array must be a JSON object with exactly two keys: 'speaker' (value '0' for {client_name}, '1' for {advisor_name}) and 'text' (string value).\n"
            f"- **Example Output:**\n"
            f"<BEGIN CONVERSATION>\n"
            f"[\n"
            f'  {{\n'
            f'    "speaker": "0",\n'
            f'    "text": "Good morning, any thoughts on {random.choice(self.company_data)["name"]}"\n'
            f"  }},\n"
            f'  {{\n'
            f'    "speaker": "1",\n'
            f'    "text": "Yes, I was just looking at {random.choice(self.company_data)["name"]}\'s recent performance."\n'
            f"  }}\n"
            f"]\n"
            f"<END CONVERSATION>\n\n"
            f"- **No Extraneous Content:** Do not include any introductory or concluding sentences, just the JSON array within the tags.\n"
            f"- **JSON Validity:** Ensure the output is valid, well-formed JSON and easily parsable.\n"
            f"- **Text Sanitization:** Ensure all text content within the JSON is properly formatted for JSON (escape special characters if needed).\n\n"
            f"**Few-Shot Examples (for {conversation_type} - Style and Format):**\n"
            f"{few_shot_examples}\n\n"
            f"<BEGIN CONVERSATION>\n[\n  {{\n    \"speaker\": \"0\" or \"1\",\n    \"text\": \"...\"\n  }},\n  ... (messages)\n]\n<END CONVERSATION>\n\n"
            f"**REMEMBER: Output ONLY the valid JSON array enclosed within the `<BEGIN CONVERSATION>` and `<END CONVERSATION>` tags.**"
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

            # Load few-shot examples (or generate them if they don't exist)
            few_shot_examples = self.load_few_shot_examples(
                conversation_type, script={"conversation_type": conversation_type, "key_companies": []} # Provide empty list for key_companies
            )  # Provide minimal script for generation

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

            # Log the conversation manifest using the dedicated logger
            manifest = json.dumps(single_conv.to_dict(), indent=4)
            self.manifest_logger.info(f"Generated Conversation Manifest (ID: {conv_id}):\n{manifest}")


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


