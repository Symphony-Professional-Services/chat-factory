"""
Generation strategy for financial advisory use case.
"""

import re
import json
import logging
import random
import os
from typing import List, Dict, Any, Tuple, Optional
import asyncio

from ..base import GenerationStrategy


class FinancialAdvisoryGenerationStrategy(GenerationStrategy):
    """
    Implementation of generation strategy for financial advisory conversations.
    
    This strategy handles the creation of financial advisory conversations, including
    prompt construction, manifest blueprints, and response processing.
    """
    
    def __init__(self, config):
        """
        Initialize the financial advisory generation strategy.
        
        Args:
            config: Configuration with generation settings
        """
        super().__init__(config)
        self.personas = getattr(config, 'PERSONAS', [])
        self.message_formats = getattr(config, 'MESSAGE_FORMATS', {})
        self.message_length_ratio = getattr(config, 'MESSAGE_LENGTH_RATIO', {
            "short": 0.4,
            "medium": 0.3,
            "long": 0.3
        })
        
        # Company targeting is optional in financial advisory
        self.company_targeting = getattr(config, 'COMPANY_TARGETING', {
            "enabled": False,
            "probability": 0.8,
            "min_companies": 1,
            "max_companies": 3
        })
        
        # Load prompt template
        self.prompt_template_path = getattr(config, 'PROMPT_TEMPLATE_PATH', 
                                          'prompts/financial_advisory/conversation_prompt.txt')
        self.prompt_template = self._load_prompt_template()
        
        # Load company data if available and targeting is enabled
        self.company_data = []
        if self.company_targeting.get("enabled", False):
            self._load_company_data()
            
    def _load_prompt_template(self) -> str:
        """Load the prompt template from file."""
        try:
            with open(self.prompt_template_path, 'r') as file:
                template = file.read()
            logging.info(f"Loaded prompt template from {self.prompt_template_path}")
            return template
        except Exception as e:
            logging.error(f"Error loading prompt template: {e}")
            # Return default template (empty string means we'll use the hardcoded version)
            return ""
    
    def _load_company_data(self):
        """Load company data from file if available."""
        company_data_file = getattr(self.config, 'COMPANY_DATA_FILE', '')
        if not company_data_file:
            logging.warning("Company data file path is empty. Cannot load company data.")
            return
        
        try:
            import csv
            with open(company_data_file, 'r') as file:
                reader = csv.DictReader(file)
                self.company_data = list(reader)
            logging.info(f"Loaded {len(self.company_data)} companies from {company_data_file}")
        except Exception as e:
            logging.error(f"Error loading company data file: {e}")
    
    def create_manifest_blueprint(self, conversation_type: str, topic: Tuple[str, str, str], 
                                 num_messages: int) -> Dict[str, Any]:
        """
        Create a manifest blueprint for a financial advisory conversation.
        
        Args:
            conversation_type: Type of conversation to generate
            topic: Selected topic as (category, topic, subtopic)
            num_messages: Number of messages to generate
            
        Returns:
            Dictionary containing blueprint for conversation generation
        """
        category, main_topic, subtopic = topic
        
        # Determine if company targeting should be enabled for this conversation
        company_targeting_enabled = False
        key_companies = []
        
        if self.company_targeting.get("enabled", False) and self.company_data and random.random() < self.company_targeting.get("probability", 0.8):
            company_targeting_enabled = True
            
            # Select number of companies to include
            min_companies = self.company_targeting.get("min_companies", 1)
            max_companies = self.company_targeting.get("max_companies", 3)
            num_companies = random.randint(min_companies, max_companies)
            
            # Select random companies
            if len(self.company_data) >= num_companies:
                selected_companies = random.sample(self.company_data, num_companies)
                key_companies = [company.get('name', '') for company in selected_companies]
        
        # Define conversation length based on the number of messages
        conversation_length = "medium"
        if num_messages < 8:
            conversation_length = "short"
        elif num_messages > 12:
            conversation_length = "long"
        
        # Get message format for this conversation type
        message_format = self.message_formats.get(conversation_type, 
                                                 self.message_formats.get(main_topic, "formal"))
        
        # Create the blueprint
        blueprint = {
            "category": category,
            "main_topic": main_topic,
            "subtopic": subtopic,
            "conversation_type": conversation_type,
            "message_format": message_format,
            "conversation_length": conversation_length,
            "company_targeting_enabled": company_targeting_enabled,
            "key_companies": key_companies,
            # Assign conversation flow characteristics
            "message_style": self._get_message_style(message_format),
            "typical_message_length": self._get_message_length_distribution(conversation_length)
        }
        
        logging.info(f"Created manifest blueprint for {category}/{main_topic}/{subtopic or ''}")
        return blueprint
    
    def _get_message_style(self, message_format: str) -> str:
        """
        Get appropriate message style based on format.
        
        Args:
            message_format: Format of the message (formal, informal, etc.)
            
        Returns:
            Description of message style
        """
        styles = {
            "formal": "professional, structured, detailed, uses industry terminology",
            "informal": "conversational, friendly, uses simpler language",
            "confidential": "discreet, careful, sensitive, focused on privacy",
            "structured": "organized, analytical, fact-based, methodical"
        }
        return styles.get(message_format, "professional, clear, helpful")
    
    def _get_message_length_distribution(self, conversation_length: str) -> Dict[str, float]:
        """
        Get message length distribution based on conversation length.
        
        Args:
            conversation_length: Length of the conversation (short, medium, long)
            
        Returns:
            Dictionary with distribution of message lengths
        """
        if conversation_length == "short":
            return {"short": 0.6, "medium": 0.3, "long": 0.1}
        elif conversation_length == "long":
            return {"short": 0.3, "medium": 0.4, "long": 0.3}
        else:  # medium
            return self.message_length_ratio
    
    async def construct_prompt(self, advisor_name: str, client_name: str, 
                        conversation_type: str, num_messages: int, 
                        manifest_blueprint: Dict[str, Any],
                        few_shot_examples: List[str]) -> str:
        """
        Construct a prompt for financial advisory conversation generation.
        
        Args:
            advisor_name: Name of the advisor
            client_name: Name of the client
            conversation_type: Type of conversation
            num_messages: Number of messages to generate
            manifest_blueprint: Blueprint for the conversation
            few_shot_examples: List of few-shot examples to include in the prompt
            
        Returns:
            Complete prompt string for LLM
        """
        category = manifest_blueprint["category"]
        main_topic = manifest_blueprint["main_topic"]
        subtopic = manifest_blueprint.get("subtopic", "")
        message_format = manifest_blueprint["message_format"]
        company_targeting_enabled = manifest_blueprint["company_targeting_enabled"]
        key_companies = manifest_blueprint["key_companies"]
        
        # Select a random persona for the advisor
        persona = random.choice(self.personas) if self.personas else "Financial Advisor"
        
        # Assign random attributes for variety
        advisor_age = random.randint(30, 60)
        communication_style = self._get_random_communication_style()
        
        # Calculate minimum viable conversation length based on requirements
        min_viable_messages = max(4, num_messages)
        
        # Use template from file if available, otherwise use default hardcoded template
        if self.prompt_template:
            # Format the template with variables
            key_companies_text = ", ".join(key_companies) if key_companies else ""
            
            # Use first names only for more natural conversation
            advisor_first_name = advisor_name.split()[0]
            client_first_name = client_name.split()[0]
            
            prompt = self.prompt_template.format(
                advisor_name=advisor_first_name,
                client_name=client_first_name,
                persona=persona,
                advisor_age=advisor_age,
                communication_style=communication_style,
                category=category,
                main_topic=main_topic,
                subtopic=subtopic,
                conversation_type=conversation_type,
                message_format=message_format,
                num_messages=num_messages,
                key_companies_text=key_companies_text
            )
        else:
            # Use the hardcoded default template for backward compatibility
            prompt = f"""You are an expert dialog generator AI that creates realistic synthetic conversations between financial advisors and their clients. Your goal is to create highly realistic, coherent dialogues that sound like genuine interactions between finance professionals and their clients.

Task: Generate a detailed, coherent conversation between {advisor_name} (a {persona}, age {advisor_age}, {communication_style}) and their client {client_name}.

# CONVERSATION PARAMETERS
- Category: {category}
- Topic Area: {main_topic}"""

            if subtopic:
                prompt += f"\n- Specific Topic: {subtopic}"
            
            prompt += f"""
- Conversation Type: {conversation_type}
- Message Format: {message_format}
- Number of Messages: Aim for approximately {num_messages} messages total

# CONVERSATIONAL DYNAMICS REQUIREMENTS
1. Create a conversation that mimics professional messaging platforms (like Symphony/Slack)
2. Maintain consistent character traits throughout the dialogue
3. The advisor should demonstrate subject-matter expertise but with a conversational messaging tone
4. The client should have realistic concerns and questions using natural chat language
5. Each message must logically follow from the previous messages
6. Use a mix of message lengths typical of chat platforms - some brief, some more detailed
7. Include specific details relevant to {main_topic} in a way that feels natural for a messaging conversation
8. Occasional brief acknowledgments are fine when they reflect natural chat flow
9. Sometimes break longer points into multiple consecutive messages (as people do when chatting)

# CONVERSATION FLOW GUIDANCE
- Most conversations (75-80%) should be INITIATED BY THE CLIENT, not the advisor
- When clients initiate, use varied natural openings (like "Hi {advisor_name}," "Question about my portfolio," "Been meaning to ask about..." etc.)
- The few advisor-initiated conversations should use varied greetings (avoid "got a sec?" - use diverse openings)
- DO NOT have participants explicitly identify themselves (they already know who they're talking to)
- Establish the context and reason for the conversation early but conversationally
- Progress naturally through the topic with questions/answers/explanations, using a messaging platform tone
- Create DEEPER conversations with multiple follow-up questions and clarifications
- Include 2-3 distinct subtopics or questions within the conversation when appropriate
- Use shorter, more direct messages rather than lengthy paragraphs
- Include natural message breaks where appropriate (someone might respond before a thought is complete)
- Use occasional professional chat shorthand where appropriate (like "Let me know what you think" → "LMK your thoughts")
- End with clear next steps, a summary, or appropriate conclusion
- IMPORTANT: The conversation should feel like authentic back-and-forth messaging, not a formal dialogue
- Generate approximately {num_messages} messages total for this conversation
"""

            # Add company targeting instructions if enabled
            if company_targeting_enabled and key_companies:
                prompt += f"""
# COMPANY REFERENCES
During the conversation, naturally incorporate discussion about these companies at appropriate moments:
{", ".join(key_companies)}

Guidelines for company references:
- Integrate mentions organically based on the financial context
- Include specific details about the companies that a financial advisor would know
- Reference company performance, news, or relevance to the client's financial situation
- Distribute references throughout the conversation, not just at the beginning or end
"""

            # Format instructions for output
            prompt += f"""
# OUTPUT FORMAT INSTRUCTIONS
Format the conversation as a series of JSON objects, EXACTLY as follows:
{{"speaker": "client", "text": "Hi {advisor_name}, I've been reading about some market volatility lately. How should I think about my retirement accounts?"}}
{{"speaker": "advisor", "text": "Good question, {client_name}. The recent volatility is actually normal given the economic indicators. Your retirement accounts are well-diversified to handle this kind of fluctuation."}}
...

IMPORTANT: 
- Use "advisor" and "client" as the speaker values (not names)
- Include only the conversation in the required JSON format
- Messages should resemble chat platform exchanges - concise, direct, and conversational
- Use the actual names ({client_name} and {advisor_name}) in the conversation naturally
- Messages should vary in length - some brief, some more detailed
- Occasionally include quick follow-up messages from the same speaker
- Do not use placeholder text - use the actual names provided
- Do not include any text outside the JSON format
- Use ONLY standard ASCII characters (avoid smart quotes, em-dashes, etc.) - use regular quotes ("), apostrophes ('), and hyphens (-)
"""

        # Add few-shot examples if available
        if few_shot_examples:
            formatted_examples = "\n# EXAMPLE CONVERSATIONS\nReference these examples for style, tone, and format:\n\n"
            for i, example in enumerate(few_shot_examples, 1):
                formatted_examples += f"EXAMPLE {i}:\n{example}\n\n"
            prompt += formatted_examples
        
        return prompt
    
    def _get_random_communication_style(self) -> str:
        """Get a random communication style for an advisor."""
        styles = [
            "professional yet approachable",
            "analytical and detailed",
            "friendly and engaging",
            "straightforward and pragmatic",
            "calm and reassuring",
            "assertive and confident",
            "professional",
            "strategic and decisive",
            "compassionate and thoughtful"
        ]
        return random.choice(styles)
    
    def process_llm_response(self, llm_response: str) -> List[Dict[str, str]]:
        """
        Process LLM response into standardized conversation format.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            List of dictionaries representing chat lines
        """
        # Clean up response and extract JSON-like structures
        lines = []
        
        # Clean and sanitize the response before processing
        sanitized_response = llm_response.strip()
        
        # Replace common Unicode characters with ASCII equivalents
        unicode_replacements = {
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Ellipsis
            '\u00a0': ' ',  # Non-breaking space
            '\u00b0': 'degrees', # Degree sign
            '\u00ae': '(R)', # Registered trademark
            '\u2122': '(TM)', # Trademark
            '\u00a9': '(c)', # Copyright
            '\u20ac': 'EUR', # Euro sign
            '\u00a3': 'GBP', # Pound sign
            '\u00a5': 'JPY', # Yen sign
            '\u2022': '*',   # Bullet
            '\u00b7': '*',   # Middle dot
        }
        
        for unicode_char, ascii_replacement in unicode_replacements.items():
            sanitized_response = sanitized_response.replace(unicode_char, ascii_replacement)
        
        # Remove any leading/trailing markdown code block markers with thorough pattern matching
        # Handle different formats of code fences
        code_block_patterns = [
            r'^```\s*json\s*\n(.*?)```\s*$',  # ```json ... ```
            r'^```\s*\n(.*?)```\s*$',         # ``` ... ```
            r'^```(.*?)```\s*$',              # ```...``` without newlines
            r'^`{1,3}(.*?)`{1,3}\s*$'         # ` ... ` or `` ... `` formats
        ]
        
        for pattern in code_block_patterns:
            match = re.search(pattern, sanitized_response, re.DOTALL)
            if match:
                sanitized_response = match.group(1).strip()
                break
        
        # If no code block pattern matched, just remove standard markers if present
        sanitized_response = re.sub(r'^```\s*json\s*', '', sanitized_response)
        sanitized_response = re.sub(r'^```', '', sanitized_response)
        sanitized_response = re.sub(r'```$', '', sanitized_response)
        sanitized_response = sanitized_response.strip()
        
        # Log the sanitized response for debugging
        logging.debug(f"Sanitized response (first 100 chars): {sanitized_response[:100]}...")
        
        try:
            # Attempt to parse the whole response as a JSON array first
            if sanitized_response.startswith('[') and sanitized_response.endswith(']'):
                try:
                    parsed_array = json.loads(sanitized_response)
                    # Validate the structure of each item in the array
                    valid_lines = []
                    for item in parsed_array:
                        if isinstance(item, dict) and "speaker" in item and "text" in item:
                            speaker_val = item["speaker"].lower()
                            # Convert to standardized speaker format
                            speaker = "1" if speaker_val == "advisor" else "0" if speaker_val == "client" else None
                            if speaker and item["text"].strip():
                                valid_lines.append({"speaker": speaker, "text": item["text"].strip()})
                    
                    if valid_lines:
                        return valid_lines
                except json.JSONDecodeError:
                    logging.debug("Could not parse response as JSON array, trying line-by-line parsing")
            
            # Try to parse as individual JSON objects on separate lines
            json_line_pattern = r'^\s*{\s*"speaker"\s*:.+}\s*$'
            if re.search(json_line_pattern, sanitized_response, re.MULTILINE):
                valid_lines = []
                for line in sanitized_response.split('\n'):
                    line = line.strip()
                    if line and line.startswith('{') and line.endswith('}'):
                        try:
                            item = json.loads(line)
                            if "speaker" in item and "text" in item:
                                speaker_val = item["speaker"].lower()
                                speaker = "1" if speaker_val == "advisor" else "0" if speaker_val == "client" else None
                                if speaker and item["text"].strip():
                                    valid_lines.append({"speaker": speaker, "text": item["text"].strip()})
                        except json.JSONDecodeError:
                            pass  # Skip lines that aren't valid JSON
                
                if valid_lines:
                    return valid_lines
            
            # Parse individual JSON objects using regex
            patterns = [
                # Standard JSON format with quoted keys
                r'{\s*"speaker"\s*:\s*"(advisor|client)"\s*,\s*"text"\s*:\s*"(.+?)"\s*}',
                # Alternative format with quotes around the whole key-value pair
                r'("speaker"\s*:\s*"(advisor|client)"\s*,\s*"text"\s*:\s*"(.+?)")',
                # Another format variant
                r'{\s*speaker\s*:\s*"(advisor|client)"\s*,\s*text\s*:\s*"(.+?)"\s*}',
                # Format where escaping might be wrong
                r'{\s*"speaker"\s*:\s*"(advisor|client)"\s*,\s*"text"\s*:\s*"([^"]+)"\s*}'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, sanitized_response, re.DOTALL)
                for match in matches:
                    if len(match.groups()) == 2:  # Standard pattern
                        speaker = "1" if match.group(1).lower() == "advisor" else "0"
                        text = match.group(2).replace('\\"', '"').replace('\\n', ' ').strip()
                        if text:
                            lines.append({"speaker": speaker, "text": text})
                    elif len(match.groups()) == 3:  # Alternative pattern
                        speaker = "1" if match.group(2).lower() == "advisor" else "0"
                        text = match.group(3).replace('\\"', '"').replace('\\n', ' ').strip()
                        if text:
                            lines.append({"speaker": speaker, "text": text})
                
                if lines:
                    break  # Found matches with this pattern, no need to try others
            
            # If still no matches, look for simple conversation patterns
            if not lines:
                # Try simple conversation format: Speaker: "Text"
                simple_patterns = [
                    r'(Advisor|Client):\s*"(.+?)"',
                    r'(Advisor|Client):\s+(.+?)(?=\n\w+:|$)',
                    r'\*\*(Advisor|Client):\*\*\s+(.+?)(?=\n\*\*|\Z)'
                ]
                
                for pattern in simple_patterns:
                    matches = re.finditer(pattern, sanitized_response, re.DOTALL | re.IGNORECASE)
                    for match in matches:
                        speaker = "1" if match.group(1).lower() == "advisor" else "0"
                        text = match.group(2).replace('\\"', '"').strip()
                        if text:
                            lines.append({"speaker": speaker, "text": text})
                    
                    if lines:
                        break  # Found matches with this pattern
                        
            # Quality checks on the extracted lines
            if lines:
                # Remove duplicates while preserving order
                seen = set()
                unique_lines = []
                for line in lines:
                    line_key = (line["speaker"], line["text"])
                    if line_key not in seen:
                        seen.add(line_key)
                        unique_lines.append(line)
                
                lines = unique_lines
                
                # Filter out empty or too short messages
                lines = [line for line in lines if len(line["text"]) > 3]
                
                # Sanitize text in each line to ensure ASCII characters only
                for line in lines:
                    # Additional Unicode character sanitization for each message
                    for unicode_char, ascii_replacement in unicode_replacements.items():
                        line["text"] = line["text"].replace(unicode_char, ascii_replacement)
                    
                    # Encode and decode to ASCII, dropping any remaining non-ASCII characters
                    try:
                        line["text"] = line["text"].encode('ascii', 'replace').decode('ascii')
                    except Exception as e:
                        logging.warning(f"Error sanitizing text to ASCII: {e}")
                
                # Ensure alternating speakers (fix if needed)
                corrected_lines = []
                expected_speaker = None
                for line in lines:
                    current_speaker = line["speaker"]
                    
                    # Initialize expected speaker with the first line's speaker
                    if expected_speaker is None:
                        expected_speaker = current_speaker
                        corrected_lines.append(line)
                    elif current_speaker == expected_speaker:
                        # Two consecutive messages from same speaker - combine them
                        if corrected_lines:
                            corrected_lines[-1]["text"] += " " + line["text"]
                    else:
                        # Different speaker, as expected
                        corrected_lines.append(line)
                    
                    # Toggle expected speaker for next message
                    expected_speaker = "0" if expected_speaker == "1" else "1"
                
                lines = corrected_lines
        
        except Exception as e:
            logging.error(f"Error processing LLM response: {e}", exc_info=True)
        
        # Quality and fallback checks
        # Ensure there's at least two messages (one from each participant)
        if not lines:
            # Create minimal conversation if nothing was parsed
            lines = [
                {"speaker": "1", "text": "Hello, how can I help you with your financial planning today?"},
                {"speaker": "0", "text": "I'd like to discuss my investment portfolio and recent market trends."}
            ]
        elif len(lines) == 1:
            # Add a response if only one message was found
            if lines[0]["speaker"] == "1":
                lines.append({"speaker": "0", "text": "That's helpful information. Could you tell me more about the options you've mentioned?"})
            else:
                lines.insert(0, {"speaker": "1", "text": "Hello, I'd be happy to discuss your financial situation and provide some guidance."})
        
        # Ensure conversation follows proper turn-taking pattern (starts with advisor)
        if lines[0]["speaker"] != "1":
            lines.insert(0, {"speaker": "1", "text": "Hello, how can I help you with your financial needs today?"})
        
        # Final quality check: ensure all messages are substantive (not generic acknowledgments)
        generic_responses = [
            "thank you for the information",
            "thank you",
            "thanks",
            "i understand",
            "that sounds good",
            "got it",
            "okay",
            "ok",
            "yes",
            "no",
            "i see"
        ]
        
        # Add context to generic messages
        for i, line in enumerate(lines):
            text_lower = line["text"].lower()
            
            # Check if this is a standalone generic response
            if any(text_lower == generic or text_lower.startswith(f"{generic}.") for generic in generic_responses):
                # Only enhance if this isn't the last message (which can be a simple closing)
                if i < len(lines) - 1:
                    # Add context based on previous message
                    if i > 0 and lines[i-1]["speaker"] != line["speaker"]:
                        prev_text = lines[i-1]["text"]
                        # Extract a topic from previous message to acknowledge
                        topic_words = [word for word in prev_text.split() if len(word) > 5 and word.lower() not in ["please", "should", "would", "about", "these", "those", "there", "where", "which", "investment", "financial"]]
                        
                        if topic_words:
                            topic = random.choice(topic_words)
                            if line["speaker"] == "0":  # Client
                                lines[i]["text"] = f"{line['text']} I'm particularly interested in what you mentioned about {topic}. Could you elaborate?"
                            else:  # Advisor
                                lines[i]["text"] = f"{line['text']} Let me provide more details about {topic} as it relates to your financial situation."
                        else:
                            # Generic enhancement if no good topic word found
                            if line["speaker"] == "0":  # Client
                                lines[i]["text"] = f"{line['text']} Could you tell me more about how this affects my specific financial situation?"
                            else:  # Advisor
                                lines[i]["text"] = f"{line['text']} Let me explain further what this means for your investment strategy."
        
        return lines