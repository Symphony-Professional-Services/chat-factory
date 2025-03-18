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

        self.temperature = config.TEMPERATURE
        self.top_p = config.TOP_P
        self.top_k = config.TOP_K

        self.project_id = config.PROJECT_ID
        self.location = config.LOCATION
        self.model_name = config.MODEL_NAME.lower()
        self.taxonomy_file = config.TAXONOMY_FILE
        self.advisor_names = config.ADVISOR_NAMES  
        self.client_names = config.CLIENT_NAMES      
        self.json_version = config.JSON_VERSION
        self.num_conversations = config.NUM_CONVERSATIONS
        self.min_messages = config.MIN_MESSAGES
        self.max_messages = config.MAX_MESSAGES
        self.topic_distribution = config.TOPIC_DISTRIBUTION

        self.taxonomy = self.load_taxonomy()
        self.flattened_topics = self.flatten_taxonomy(self.taxonomy)
        self.conversation_type_metadata = self.taxonomy.get("conversation_types", {})

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

        # Create a dedicated logger for conversation manifests with run_id in the file name
        self.manifest_logger = logging.getLogger("conversation_manifest")
        self.manifest_logger.setLevel(logging.INFO)
        if not self.manifest_logger.handlers:
            manifest_log_file = self.conversation_manifest_dir / f"conversation_manifest_{self.run_id}.log"
            fh = logging.FileHandler(manifest_log_file)
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.manifest_logger.addHandler(fh)

    def load_company_data(self) -> List[Dict]:
        """Loads company data from the CSV file."""
        company_data: List[Dict] = []
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
        try:
            with open(self.taxonomy_file, 'r') as f:
                taxonomy = json.load(f)
                logging.info(f"Loaded taxonomy from {self.taxonomy_file}.")
                return taxonomy
        except Exception as e:
            logging.error(f"Error loading taxonomy file: {e}")
            raise

    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str]]:
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

    def select_conversation_type(self) -> str:
        conversation_type = random.choice(self.conversation_types)
        logging.debug(f"Selected conversation type: {conversation_type}")
        return conversation_type

    def get_message_format(self, conversation_type: str) -> str:
        message_format = self.message_formats.get(conversation_type, "formal")
        logging.debug(f"Message format for {conversation_type}: {message_format}")
        return message_format

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
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k
            )
            response = await self.llm.generate_content_async(
                contents=[prompt],
                generation_config=generation_config,
                stream=False
            )
            raw_response = response.candidates[0].content.text.strip()
            logging.debug(f"Raw LLM Response: {raw_response}")
            return raw_response
        except Exception as e:
            logging.error(f"Error calling Vertex AI: {e}", exc_info=True)
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

    def select_topic(self) -> Tuple[str, str]:
        if self.topic_distribution == "uniform":
            category, topic = random.choice(self.flattened_topics)
            logging.debug(f"Selected topic (uniform): {category} - {topic}")
            return category, topic
        else:
            category, topic = random.choice(self.flattened_topics)
            logging.debug(f"Selected topic (default): {category} - {topic}")
            return category, topic

    # --- New: Create Manifest Blueprint ---
    # def create_manifest_blueprint(self, conversation_type: str, num_messages: int) -> dict:
    #     # For illustration, we use static primary_topic; you could enhance this logic.
    #     primary_topic = "Q2 2024 Tech Earnings"
    #     key_companies = random.sample([c['name'] for c in self.company_data], min(3, len(self.company_data)))
    #     conversation_length = "medium" if num_messages < 8 else ("long" if num_messages > 12 else "short")
    #     blueprint = {
    #         "conversation_type": conversation_type,
    #         "primary_topic": primary_topic,
    #         "key_companies": key_companies,
    #         "conversation_length": conversation_length,
    #         "persona_advisor": self.select_persona(),
    #         "persona_client": self.select_persona(),
    #         "conversation_flow": [
    #             {"speaker": "advisor", "topic": "Initial market overview"},
    #             {"speaker": "client", "topic": "Questions about specific companies"},
    #             {"speaker": "advisor", "topic": "Analysis of earnings and performance"},
    #             {"speaker": "client", "topic": "Follow-up and comparison"}
    #         ]
    #     }
    #     return blueprint

    def create_manifest_blueprint(self, conversation_type: str, num_messages: int) -> dict:
        # Get metadata for this conversation type from the taxonomy.
        conv_meta = self.conversation_type_metadata.get(conversation_type, {})
        # Use the taxonomy's primary_topic if it exists; otherwise, default to the conversation type.
        primary_topic = conv_meta.get("primary_topic", conversation_type)
        
        # Determine the number of companies to include based on conversation type.
        num_companies = self.select_company_count(conversation_type)
        key_companies = random.sample(
            [c['name'] for c in self.company_data],
            min(num_companies, len(self.company_data))
        )
        
        # Define conversation length based on the number of messages.
        conversation_length = "medium" if num_messages < 8 else ("long" if num_messages > 12 else "short")
        
        blueprint = {
            "conversation_type": conversation_type,
            "primary_topic": primary_topic,
            "key_companies": key_companies,
            "conversation_length": conversation_length,
            "persona_advisor": self.select_persona(),
            "persona_client": self.select_persona(),
            "conversation_flow": [
                {"speaker": "advisor", "topic": "Initial market overview"},
                {"speaker": "client", "topic": "Questions about specific companies"},
                {"speaker": "advisor", "topic": "Analysis of earnings and performance"},
                {"speaker": "client", "topic": "Follow-up and comparison"}
            ]
        }
        return blueprint


    # def parse_response(self, response: str, expected_messages: int) -> List[ChatLine]:
    #     try:
    #         start_tag = "<BEGIN CONVERSATION>"
    #         end_tag = "<END CONVERSATION>"

    #         start = response.find(start_tag)
    #         end = response.find(end_tag)

    #         if start == -1 or end == -1:
    #             logging.error("Missing conversation tags in the LLM response.")
    #             logging.debug(f"Full LLM Response: {response}")
    #             return []

    #         json_str = response[start + len(start_tag):end].strip()

    #         if not json_str.startswith("[") or not json_str.endswith("]"):
    #             logging.error("JSON array not found within conversation tags.")
    #             logging.debug(f"Extracted JSON string: {json_str}")
    #             return []

    #         # Sanitize the JSON string by escaping backslashes and quotes
    #         # Alternatively, use more sophisticated sanitization if needed
    #         json_str = json_str.encode('utf-8', 'ignore').decode('utf-8')
    #         data = json.loads(json_str)

    #         if not isinstance(data, list):
    #             logging.error("Parsed JSON is not a list.")
    #             logging.debug(f"Parsed JSON data: {data}")
    #             return []

    #         lines = []
    #         for index, line in enumerate(data):
    #             if not isinstance(line, dict):
    #                 logging.error(f"Message at index {index} is not a dictionary.")
    #                 continue
    #             if "speaker" not in line or "text" not in line:
    #                 logging.error(f"Message at index {index} missing 'speaker' or 'text' keys.")
    #                 continue
    #             # Further sanitize text fields
    #             text = line["text"].encode('utf-8', 'ignore').decode('utf-8')
    #             lines.append(ChatLine(speaker=line["speaker"], text=text))

    #         if len(lines) != expected_messages:
    #             logging.warning(f"Expected {expected_messages} messages, but got {len(lines)}.")

    #         return lines
    #     except json.JSONDecodeError as e:
    #         logging.error(f"JSON decoding error: {e}")
    #         logging.debug(f"Malformed JSON: {response}")
    #         return []
    #     except Exception as e:
    #         logging.error(f"Error parsing response: {e}")
    #         logging.debug(f"Response content: {response}")
    #         return []


    def select_company_count(self, conversation_type: str) -> int:
        conv_meta = self.conversation_type_metadata.get(conversation_type, {})
        if "company_count_options" in conv_meta:
            options = conv_meta["company_count_options"]
            count = random.choice(options)
        else:
            # Fallback if conversation_type is not explicitly mapped.
            count = random.choice([1, 2])
        logging.debug(f"select_company_count: For conversation_type '{conversation_type}', selected count: {count}")
        return count

    # --- Updated: construct_prompt now accepts manifest_blueprint ---
    # def construct_prompt(
    #     self,
    #     advisor_name: str,
    #     client_name: str,
    #     conversation_type: str,
    #     num_messages: int,
    #     manifest_blueprint: dict
    # ) -> str:
    #     # Embed the manifest blueprint in the prompt for LLM guidance.
    #     manifest_str = json.dumps(manifest_blueprint, indent=4)
    #     prompt_header = f"Manifest Blueprint (OUTLINE OF CONVERSATION):\n{manifest_str}\n\n"

    #     message_format = self.get_message_format(conversation_type)
    #     conversation_metadata = self.conversation_type_metadata.get(conversation_type, {})
    #     message_style = conversation_metadata.get("message_style", "professional")

    #     # Get company name variations and example companies prompt
    #     example_companies_prompt = ""
    #     company_example_count = self.select_company_count(conversation_type)
    #     example_companies = random.sample(self.company_data, company_example_count)
    #     for company_dict in example_companies:
    #         company = company_dict['name']
    #         variations = [company]
    #         if company_dict.get('variations'):
    #             variations.extend(company_dict['variations'])
    #         if company_dict.get('abbreviations'):
    #             variations.extend(company_dict['abbreviations'])
    #         ticker = company_dict.get('ticker')
    #         if ticker:
    #             variations.append(ticker)
    #         example_companies_prompt += f"- **{company}**: Variations like: {', '.join(set(variations))}\n"

    #     few_shot_examples = self.load_few_shot_examples(conversation_type)
    #     message_length_guidance = self.get_message_length_guidance(num_messages)

    #     prompt_body = (
    #         f"Generate a realistic and {message_format} chat conversation focused on **{conversation_type}** between two financial professionals on Symphony. "
    #         f"The primary goal is company mentions for tagging, with varied message lengths.\n\n"
    #         f"Financial Professional 1 (Advisor): {advisor_name}, Persona: {self.select_persona()}\n"
    #         f"Financial Professional 2 (Client): {client_name}, Persona: {self.select_persona()}\n\n"
    #         f"Conversation Topic: {conversation_type}\n"
    #         f"Message Format: {message_format}\n\n"
    #         f"**Company Mention Guidelines:**\n"
    #         f"- MUST heavily feature company mentions from the provided list, using varied formats (formal, abbreviations, tickers, misspellings).\n"
    #         f"- Example Company Variations:\n{example_companies_prompt}"
    #         f"- Company List Examples (see config.COMPANY_DATA_FILE):\n"
    #     )
    #     for i in range(min(5, len(self.company_data))):
    #         prompt_body += f"  - {self.company_data[i]['name']} ({self.company_data[i].get('ticker', '')})\n"
    #     prompt_body += (
    #         f"-.\n" # and more
    #         f"- Ticker Examples (from COMPANY_DATA_FILE): {', '.join(set(c['ticker'] for c in self.company_data if c.get('ticker')))}\n"
    #         f"- Abbreviation Examples (from COMPANY_DATA_FILE): {', '.join(set(abbr for c in self.company_data if c.get('abbreviations') for abbr in c['abbreviations']))}\n"
    #         f"- Misspelling Examples (from COMPANY_DATA_FILE): {', '.join(set(misspelling for c in self.company_data if c.get('misspellings') for misspelling in c['misspellings']))}\n\n"
    #         f"**Message Length and Style Guidelines:**\n"
    #         f"1. Generate a conversation with **exactly {num_messages} messages**, with message lengths guided as follows:\n"
    #         f"   - **Message Length Distribution:** [ {', '.join(message_length_guidance)} ] (This is guidance, try to approximate).\n"
    #         f"   - **Short Messages:** A few words.\n"
    #         f"   - **Medium Messages:** A sentence or two providing some context or detail.\n"
    #         f"   - **Long Messages:** Multi-sentence messages, like market updates or stock analysis excerpts.\n"
    #         f"2. Maintain a {message_format} and professional tone.\n"
    #         f"3. Be concise and professional.\n"
    #         f"4. Focus on realistic financial discussions.\n"
    #         f"5. Integrate multiple company mentions within messages naturally.\n\n"
    #         f"**Conversation Flow Guidelines:**\n"
    #         f"7. Conversation initiation can be by either professional.\n"
    #         f"8. Speakers should alternate naturally.\n"
    #         f"9. Conversation should have a logical flow and progression, with each message relating to the previous ones.\n\n"
    #         f"**Instructions for Output Format - VERY IMPORTANT!**\n"
    #         f"- **Output Format:** Structure the ENTIRE conversation as a **single JSON array** enclosed within the **EXACT** tags: `<BEGIN CONVERSATION>` and `<END CONVERSATION>`. Do not include any other text outside these tags.\n"
    #         f"- **Message Object Structure:** Each message in the JSON array must be a JSON object with exactly two keys: 'speaker' (value '0' for {client_name}, '1' for {advisor_name}) and 'text' (string value).\n"
    #         f"- **Example Output:**\n"
    #         f"<BEGIN CONVERSATION>\n"
    #         f"[\n"
    #         f'  {{\n'
    #         f'    "speaker": "0",\n'
    #         f'    "text": "Good morning, any thoughts on {random.choice(self.company_data)["name"]}"\n'
    #         f"  }},\n"
    #         f'  {{\n'
    #         f'    "speaker": "1",\n'
    #         f'    "text": "Yes, I was just looking at {random.choice(self.company_data)["name"]}\'s recent performance."\n'
    #         f"  }}\n"
    #         f"]\n"
    #         f"<END CONVERSATION>\n\n"
    #         f"- **No Extraneous Content:** Do not include any introductory or concluding sentences, just the JSON array within the tags.\n"
    #         f"- **JSON Validity:** Ensure the output is valid, well-formed JSON and easily parsable.\n"
    #         f"- **Text Sanitization:** Ensure all text content within the JSON is properly formatted for JSON (escape special characters if needed).\n\n"
    #         f"**Few-Shot Examples (for {conversation_type} - Style and Format):**\n"
    #         f"{few_shot_examples}\n\n"
    #         f"<BEGIN CONVERSATION>\n[\n  {{\n    \"speaker\": \"0\" or \"1\",\n    \"text\": \"...\"\n  }},\n  ... (messages)\n]\n<END CONVERSATION>\n\n"
    #         f"**REMEMBER: Output ONLY the valid JSON array enclosed within the `<BEGIN CONVERSATION>` and `<END CONVERSATION>` tags.**"
    #     )
    #     full_prompt = prompt_header + prompt_body
    #     logging.debug(f"Constructed Prompt: {full_prompt}")
    #     return full_prompt
    def construct_prompt(
        self,
        advisor_name: str,
        client_name: str,
        conversation_type: str,
        num_messages: int,
        manifest_blueprint: dict
    ) -> str:
        """
        Constructs the prompt for the LLM by embedding the manifest blueprint and
        clear, explicit instructions on the expected output format.
        """
        # Embed the blueprint and add explicit formatting instructions.
        manifest_str = json.dumps(manifest_blueprint, indent=4)
        prompt_header = (
            "Manifest Blueprint (OUTLINE OF CONVERSATION):\n"
            f"{manifest_str}\n\n"
            "IMPORTANT: Return a valid JSON object with a single key 'conversations'.\n"
            "The value of 'conversations' must be a JSON array containing exactly "
            f"{num_messages} message objects. Each message object must have exactly two keys:\n"
            "    'speaker': '0' (client) or '1' (advisor), and\n"
            "    'text': a string representing the message text.\n"
            "Do not include any extra keys or text outside this JSON object.\n\n"
        )

        message_format = self.get_message_format(conversation_type)
        conversation_metadata = self.conversation_type_metadata.get(conversation_type, {})
        # Build example companies prompt:
        example_companies_prompt = ""
        company_example_count = self.select_company_count(conversation_type)
        example_companies = random.sample(self.company_data, company_example_count)
        for company_dict in example_companies:
            company = company_dict['name']
            variations = [company]
            if company_dict.get('variations'):
                variations.extend(company_dict['variations'])
            if company_dict.get('abbreviations'):
                variations.extend(company_dict['abbreviations'])
            ticker = company_dict.get('ticker')
            if ticker:
                variations.append(ticker)
            example_companies_prompt += f"- **{company}**: Variations like: {', '.join(set(variations))}\n"

        few_shot_examples = self.load_few_shot_examples(conversation_type)
        message_length_guidance = self.get_message_length_guidance(num_messages)

        prompt_body = (
            f"Generate a realistic and {message_format} chat conversation focused on **{conversation_type}** "
            "between two financial professionals on Symphony. The conversation must strictly follow the Manifest Blueprint's guidelines.\n\n"
            f"Financial Professional 1 (Advisor): {advisor_name}, Persona: {self.select_persona()}\n"
            f"Financial Professional 2 (Client): {client_name}, Persona: {self.select_persona()}\n\n"
            f"Conversation Topic: {conversation_type}\n"
            f"Message Format: {message_format}\n\n"
            f"**Company Mention Guidelines:**\n"
            f"- ONLY mention the companies specified in the Manifest Blueprint's 'key_companies' field.\n"
            f"- Example Company Variations:\n{example_companies_prompt}\n"
            f"**Message Length and Style Guidelines:**\n"
            f"- Produce exactly {num_messages} messages with the following approximate length distribution: [ {', '.join(message_length_guidance)} ].\n"
            f"- Maintain a {message_format} and professional tone.\n"
            f"- Ensure natural alternation between speakers and follow the provided conversation flow.\n\n"
            f"**Instructions for Output Format:**\n"
            f"- Return ONLY the valid JSON object (do not include any additional text) enclosed within the tags `<BEGIN CONVERSATION>` and `<END CONVERSATION>`.\n"
            f"- Each message object must have exactly two keys: 'speaker' and 'text'.\n\n"
            f"**Few-Shot Examples (for {conversation_type}):**\n"
            f"{few_shot_examples}\n\n"
            "Example:\n"
            "<BEGIN CONVERSATION>\n"
            "[\n"
            '  {"speaker": "0", "text": "Good morning, any thoughts on Apple Inc.?"},\n'
            '  {"speaker": "1", "text": "Yes, I believe Apple Inc. is showing strong performance."}\n'
            "]\n"
            "<END CONVERSATION>\n\n"
            "REMEMBER: Output ONLY the valid JSON object enclosed within the `<BEGIN CONVERSATION>` and `<END CONVERSATION>` tags."
        )

        full_prompt = prompt_header + prompt_body
        logging.debug(f"Constructed Prompt (in {__file__}:{__import__('inspect').currentframe().f_lineno}): {full_prompt}")
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


    # --- Updated: generate_conversation now accepts manifest_blueprint ---
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
                    lines=lines
                )
            except Exception as e:
                logging.error(f"Error generating conversation on attempt {attempt}: {e}", exc_info=True)
        logging.error(f"Failed to generate a valid conversation after {max_retries} attempts.")
        return SingleConversation(
            conversation_id="",
            timestamp="",
            category=conversation_type,
            topic=conversation_type,
            lines=[]
        )

    async def process_conversation(
        self,
        conv_number: int,
        conversation_type: str,
        advisor_name: str,
        client_name: str,
        num_messages: int
    ):
        """
        Processes and buffers a single conversation.
        """
        try:
            logging.debug(f"Processing Conversation {conv_number}: Advisor - {advisor_name}, Client - {client_name}")
            # Create manifest blueprint as a blueprint for the conversation
            blueprint = self.create_manifest_blueprint(conversation_type, num_messages)
            # Load few-shot examples (using the blueprint as script)
            few_shot_examples = self.load_few_shot_examples(conversation_type, script=blueprint)
            # Generate the conversation using the blueprint
            single_conv = await self.generate_conversation(advisor_name, client_name, conversation_type, num_messages, manifest_blueprint=blueprint)
            if not single_conv.lines:
                logging.warning(f"Conversation {conv_number} between {advisor_name} and {client_name} has no messages. Skipping.")
                return

            conv_id = f"conv_{conv_number:04d}"
            timestamp = datetime.utcnow().isoformat() + "Z"
            single_conv.conversation_id = conv_id
            single_conv.timestamp = timestamp

            key = (advisor_name, client_name)
            if key not in self.conversation_buffer:
                self.conversation_buffer[key] = ConversationFile(
                    version=self.json_version,
                    advisor=advisor_name,
                    client=client_name,
                    conversations=[]
                )
            self.conversation_buffer[key].conversations.append(single_conv)

            # Create final manifest that includes both the blueprint and the generated conversation
            final_manifest = {
                "blueprint": blueprint,
                "generated_conversation": single_conv.to_dict()
            }
            self.manifest_logger.debug(f"Generated Conversation Manifest (ID: {conv_id}):\n{json.dumps(final_manifest, indent=4)}")
            logging.info(f"Generated conversation {conv_number}/{self.num_conversations} between {advisor_name} and {client_name}")
        except Exception as e:
            logging.error(f"Failed to process conversation {conv_number}: {e}", exc_info=True)

    async def generate_synthetic_data(self):
        tasks = []
        for i in range(1, self.num_conversations + 1):
            conversation_type = self.select_conversation_type()
            advisor, client = self.select_advisors_clients()
            num_messages = random.randint(self.min_messages, self.max_messages)
            tasks.append(self.process_conversation(i, conversation_type, advisor, client, num_messages))
        await asyncio.gather(*tasks)
        for (advisor, client), conv_file in self.conversation_buffer.items():
            try:
                self.save_conversation_file(advisor, client, conv_file)
            except Exception as e:
                logging.error(f"Failed to save conversations for {advisor} and {client}: {e}")

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
