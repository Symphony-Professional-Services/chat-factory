
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

import asyncio
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
        self.project_id = config.PROJECT_ID
        self.location = config.LOCATION
        self.model_name = config.MODEL_NAME.lower()
        self.taxonomy_file = config.TAXONOMY_FILE
        self.advisor_names = config.ADVISOR_NAMES  
        self.client_names = config.CLIENT_NAMES      
        self.output_dir = Path(config.OUTPUT_DIR)
        self.json_version = config.JSON_VERSION
        self.num_conversations = config.NUM_CONVERSATIONS
        self.min_messages = config.MIN_MESSAGES
        self.max_messages = config.MAX_MESSAGES
        self.topic_distribution = config.TOPIC_DISTRIBUTION

        self.taxonomy = self.load_taxonomy()
        self.flattened_topics = self.flatten_taxonomy(self.taxonomy)
        self.setup_output_directory()
        self.initialize_vertex_ai()
        self.conversation_buffer = {}  # Buffer to hold conversations per advisor-client pair

    def load_taxonomy(self) -> Dict[str, Any]:
        """Loads in taxonomy of topics to choose from."""
        try:
            with open(self.taxonomy_file, 'r') as f:
                taxonomy = json.load(f)
                logging.info(f"Loaded taxonomy from {self.taxonomy_file}.")
                return taxonomy
        except Exception as e:
            logging.error(f"Error loading taxonomy file: {e}")
            raise

    def flatten_taxonomy(self, taxonomy: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Flatten the nested taxonomy into a list of tuples (Category, Topic).
        """
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

    def setup_output_directory(self):
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Output directory set up at {self.output_dir}")
        except Exception as e:
            logging.error(f"Error setting up output directory: {e}")
            raise

    def initialize_vertex_ai(self):
        try:
            os.environ['GOOGLE_CLOUD_PROJECT'] = self.project_id
            os.environ['GOOGLE_CLOUD_LOCATION'] = self.location
            self.llm = GenerativeModel(model_name=self.model_name)
            logging.info(f"Initialized GenerativeModel with model name '{self.model_name}'.")
        except Exception as e:
            logging.error(f"Error initializing Vertex AI GenerativeModel: {e}")
            raise

    def select_topic(self) -> Tuple[str, str]:
        if self.topic_distribution == "uniform":
            category, topic = random.choice(self.flattened_topics)
            logging.debug(f"Selected topic (uniform): {category} - {topic}")
            return category, topic
        else:
            # Implement custom distribution logic if needed
            category, topic = random.choice(self.flattened_topics)
            logging.debug(f"Selected topic (default): {category} - {topic}")
            return category, topic

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

    def construct_prompt(
        self, 
        advisor_name: str, 
        client_name: str, 
        category: str, 
        topic: str, 
        num_messages: int
    ) -> str:
        """
        Constructs an optimized prompt for generating a realistic and varied chat conversation between a financial advisor and a high net worth client.
        """
        # Assign random attributes
        advisor_age, advisor_comm = self.assign_random_attributes()
        client_age, client_comm = self.assign_random_attributes()

        # Few-shot examples demonstrating both advisor-initiated and client-initiated conversations
        example_conversations = """
        <BEGIN CONVERSATION>
        [
        {
            "speaker": "1",
            "text": "Good morning, Allen. I noticed you've been considering sustainable investments. Shall we explore some options?"
        },
        {
            "speaker": "0",
            "text": "Good morning, Alice. Yes, I'm interested in understanding how ESG-focused ETFs can fit into my portfolio."
        },
        {
            "speaker": "1",
            "text": "Absolutely. ESG ETFs can provide both growth potential and alignment with your sustainability goals. Would you like to review some specific funds?"
        },
        {
            "speaker": "0",
            "text": "That would be great. I'm particularly interested in funds that have a strong track record in environmental impact."
        },
        {
            "speaker": "1",
            "text": "Understood. Let's look at a few top-performing ESG ETFs that meet your criteria."
        }
        ]
        <END CONVERSATION>

        <BEGIN CONVERSATION>
        [
        {
            "speaker": "0",
            "text": "Hi Bob, I've been thinking about setting up a trust for my estate planning. Can you provide some insights?"
        },
        {
            "speaker": "1",
            "text": "Of course, Diana. Establishing a trust can offer significant benefits, including estate tax optimization and asset protection. Do you have a specific type of trust in mind?"
        },
        {
            "speaker": "0",
            "text": "I'm not entirely sure. What are the main differences between a revocable and an irrevocable trust?"
        },
        {
            "speaker": "1",
            "text": "A revocable trust offers flexibility, allowing you to make changes as needed, while an irrevocable trust provides greater asset protection and potential tax advantages. It depends on your long-term goals."
        },
        {
            "speaker": "0",
            "text": "I see. Let's schedule a meeting to discuss which option aligns best with my family's needs."
        }
        ]
        <END CONVERSATION>

        <BEGIN CONVERSATION>
        [
        {
            "speaker": "1",
            "text": "Good afternoon, Betty. I wanted to touch base regarding your recent interest in tax optimization strategies. Shall we delve into some tailored options?"
        },
        {
            "speaker": "0",
            "text": "Good afternoon, Carol. Yes, I'd like to understand how I can better structure my investments to minimize tax liabilities."
        },
        {
            "speaker": "1",
            "text": "Certainly. We can explore options such as tax-loss harvesting, municipal bonds, and utilizing tax-advantaged accounts. Which areas are you most interested in?"
        },
        {
            "speaker": "0",
            "text": "I'm particularly interested in tax-efficient funds and how I can leverage my retirement accounts for better tax outcomes."
        },
        {
            "speaker": "1",
            "text": "Great choices. Let's analyze your current portfolio and identify specific funds that align with your tax optimization goals."
        }
        ]
        <END CONVERSATION>

        <BEGIN CONVERSATION>
        [
        {
            "speaker": "0",
            "text": "Alice, I've been reviewing my financial statements and noticed some discrepancies. Can we go over them?"
        },
        {
            "speaker": "1",
            "text": "Certainly, Allen. Let's schedule a time to review your statements in detail and address any concerns you have."
        },
        {
            "speaker": "0",
            "text": "Thank you. I appreciate your prompt attention to this matter."
        }
        ]
        <END CONVERSATION>
        """
        # ============================================ 
        # MAIN PROMPT FOR GENERATION CONVERSATION DATA
        # ============================================
        prompt = (
            f"Generate a realistic and professional chat conversation between a financial advisor and their high net worth client based on the following details. The conversation is taking place on a chat messaging platform called Symphony - very similar to slack.:\n\n"
            f"**Financial Advisor:** {advisor_name}\n"
            f"- **Age:** {advisor_age}\n"
            f"- **Communication Style:** {advisor_comm}\n\n"
            f"**Client:** {client_name}\n"
            f"- **Age:** {client_age}\n"
            f"- **Occupation:** High Net Worth Individual\n"
            f"- **Net Worth:** High net worth individual.\n"
            f"- **Communication Style:** {client_comm}\n\n"
            f"**Context:**\n"
            f"- The conversation topic is: '{topic}' within the category '{category}'.\n"
            f"- The conversation should reflect the client's status as a high net worth individual, focusing on relevant and sophisticated financial strategies.\n"
            f"- Include brief, casual remarks where appropriate to add realism, but maintain a professional tone throughout the conversation.\n\n"
            f"**Conversation Guidelines:**\n"
            f"1. The conversation should consist of approximately {num_messages} exchanges (messages), but slight variations are acceptable.\n"
            f"2. Either the advisor or the client can initiate the conversation to introduce variability.\n"
            f"3. Alternate between the advisor and client to mimic a natural dialogue flow (doesn't need to just be back and forth).\n"
            f"4. Messages should be concise, clear, and to the point, avoiding unnecessary verbosity.\n"
            f"5. Utilize natural, professional language; avoid robotic or overly formal phrasing. Vary the conversations in length, language, brevity, etc.\n"
            f"6. Incorporate subtopics related to the main topic that are pertinent to high net worth individuals.\n\n"
            f"**Instructions:**\n"
            f"- **Do Not:** Include internal thoughts, reasoning, or explanations outside of the dialogue.\n"
            f"- **Do Not:** Add any sensitive personal information or identifiable details.\n"
            f"- **Ensure:** The conversation flows logically, with each message building upon the previous ones.\n"
            f"- **Format:** Output the conversation as a JSON array enclosed within `<BEGIN CONVERSATION>` and `<END CONVERSATION>` tags. Each message should be an object with the following structure:\n\n"
            f"{example_conversations}\n\n"
            f"<BEGIN CONVERSATION>\n"
            f"[\n"
            f"  {{\n"
            f"    \"speaker\": \"0\" or \"1\",\n"
            f"    \"text\": \"...\"\n"
            f"  }},\n"
            f"  ... (additional messages)\n"
            f"]\n"
            f"<END CONVERSATION>\n\n"
            f"**Important:**\n"
            f"- **Only Output:** The JSON array enclosed within the specified tags. Do not include any additional text, explanations, or code syntax.\n"
            f"- **Validity:** Ensure the JSON is well-formed and parsable without errors.\n"
            f"- **Sanitization:** Ensure that all special characters in the text fields are properly escaped or removed to maintain JSON integrity.\n"
        )
        logging.debug(f"Constructed Prompt: {prompt}")
        return prompt

    async def call_vertex_ai(self, prompt: str) -> str:
        try:
            generation_config = GenerationConfig(
                max_output_tokens=1200,
                temperature=0.2,
                top_p=1,
                top_k=32
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
        category: str, 
        topic: str, 
        num_messages: int,
        max_retries: int = 3
    ) -> SingleConversation:
        """
        Generates a single conversation between a financial advisor and a high net worth client.

        Parameters:
        - advisor_name (str): Name of the advisor.
        - client_name (str): Name of the client.
        - category (str): The main category of the conversation topic.
        - topic (str): The specific topic of discussion.
        - num_messages (int): The number of messages in the conversation.
        - max_retries (int): Maximum number of retries for generating a valid conversation.

        Returns:
        - SingleConversation: Dataclass instance containing the generated conversation details.
        """
        for attempt in range(1, max_retries + 1):
            try:
                prompt = self.construct_prompt(advisor_name, client_name, category, topic, num_messages)          
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

                # Create and return a SingleConversation instance (ID and timestamp will be set in process_conversation)
                return SingleConversation(
                    conversation_id="",
                    timestamp="",        
                    category=category,
                    topic=topic,
                    lines=lines
                )
            
            except Exception as e:
                logging.error(f"Error generating conversation on attempt {attempt}: {e}", exc_info=True)

        logging.error(f"Failed to generate a valid conversation after {max_retries} attempts.")
        return SingleConversation(
            conversation_id="",
            timestamp="",
            category=category,
            topic=topic,
            lines=[]
        )

    async def process_conversation(
            self, 
            conv_number: int, 
            category: str, 
            topic: str, 
            advisor_name: str, 
            client_name: str, 
            num_messages: int
        ):
        """
        Processes a single conversation by generating it and buffering the result.

        Parameters:
        - conv_number (int): The conversation number (for unique ID and logging).
        - category (str): The main category of the conversation topic.
        - topic (str): The specific topic of discussion.
        - advisor_name (str): The name of the advisor.
        - client_name (str): The name of the client.
        - num_messages (int): The number of messages in the conversation.
        """
        try:
            # Log the advisor and client names being used
            logging.debug(f"Processing Conversation {conv_number}: Advisor - {advisor_name}, Client - {client_name}")

            # Generate the conversation
            single_conv = await self.generate_conversation(advisor_name, client_name, category, topic, num_messages)
            
            if not single_conv.lines:
                logging.warning(f"Conversation {conv_number} between {advisor_name} and {client_name} has no messages. Skipping.")
                return

            # Generate unique conversation ID and timestamp
            conv_id = f"conv_{conv_number:04d}"
            timestamp = datetime.utcnow().isoformat() + "Z"

            # Update the single_conv with ID and timestamp
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

    def save_conversation_file(self, advisor: str, client: str, conversation_file: ConversationFile):
        """
        Saves the conversation file as a JSON file in the specified output directory.

        Parameters:
        - advisor (str): The name of the advisor.
        - client (str): The name of the client.
        - conversation_file (ConversationFile): The conversation file data.
        """
        sanitized_advisor = sanitize_filename(advisor)
        sanitized_client = sanitize_filename(client)

        advisor_dir = self.output_dir / sanitized_advisor
        filename = f"{sanitized_client}.json"  # Single file per advisor-client pair
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

    async def generate_synthetic_data(self):
        tasks = []
        for i in range(1, self.num_conversations + 1):
            category, topic = self.select_topic()
            advisor, client = self.select_advisors_clients()
            num_messages = random.randint(self.min_messages, self.max_messages)
            tasks.append(self.process_conversation(i, category, topic, advisor, client, num_messages))
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)

        for (advisor, client), conv_file in self.conversation_buffer.items():
            try:
                self.save_conversation_file(advisor, client, conv_file)
            except Exception as e:
                logging.error(f"Failed to save conversations for {advisor} and {client}: {e}")

def main():
    try:
        generator = SyntheticChatGenerator(config)
        asyncio.run(generator.generate_synthetic_data())
        logging.info("Synthetic chat data generation completed successfully.")
    except Exception as e:
        logging.critical(f"Critical error in synthetic chat data generation: {e}")

if __name__ == "__main__":
    main()

