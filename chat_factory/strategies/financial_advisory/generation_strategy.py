"""
Generation strategy for financial advisory use case.
"""

import re
import json
import logging
import random
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
        
        # Load company data if available and targeting is enabled
        self.company_data = []
        if self.company_targeting.get("enabled", False):
            self._load_company_data()
    
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
        subtopic = manifest_blueprint["subtopic"]
        message_format = manifest_blueprint["message_format"]
        company_targeting_enabled = manifest_blueprint["company_targeting_enabled"]
        key_companies = manifest_blueprint["key_companies"]
        
        # Select a random persona for the advisor
        persona = random.choice(self.personas) if self.personas else "Financial Advisor"
        
        # Assign random attributes for variety
        advisor_age = random.randint(30, 60)
        communication_style = self._get_random_communication_style()
        
        # Build the prompt
        prompt = f"""You are a conversation generator AI that creates realistic synthetic conversations between a financial advisor and their client.

Generate a conversation between {advisor_name} (a {persona}, age {advisor_age}, {communication_style}) and their client {client_name}.

Conversation Category: {category}
Topic Area: {main_topic}"""

        if subtopic:
            prompt += f"\nSpecific Topic: {subtopic}"
        
        prompt += f"""
Conversation Type: {conversation_type}
Message Format: {message_format}
Number of Messages: {num_messages}

The conversation should be natural and realistic, showing both participants engaging meaningfully on the topic. The advisor should demonstrate expertise and professionalism, while the client should ask relevant questions and express concerns.
"""

        # Add company targeting instructions if enabled
        if company_targeting_enabled and key_companies:
            prompt += f"""
During the conversation, naturally mention and discuss the following companies:
{", ".join(key_companies)}

Ensure the companies are integrated naturally into the discussion, relevant to the conversation topic, and not forced or artificial.
"""

        # Format instructions for output
        prompt += """
Format the conversation exactly as follows:
{"speaker": "advisor", "text": "Hello [client name], how can I help you today?"}
{"speaker": "client", "text": "Hi [advisor name], I'm interested in discussing [topic]."}
...

Do not include any other text, explanations, or commentary outside of this format.
"""

        # Add few-shot examples if available
        if few_shot_examples:
            formatted_examples = "\nHere are some example conversations similar to what I want you to generate:\n\n"
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
            "informal yet professional",
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
        
        try:
            # First try to parse the whole response as a JSON array
            if llm_response.strip().startswith('[') and llm_response.strip().endswith(']'):
                try:
                    lines = json.loads(llm_response)
                    return lines
                except json.JSONDecodeError:
                    pass  # Fall back to line-by-line parsing
            
            # Parse individual JSON objects
            pattern = r'{\s*"speaker"\s*:\s*"(advisor|client)"\s*,\s*"text"\s*:\s*"(.+?)"\s*}'
            matches = re.finditer(pattern, llm_response, re.DOTALL)
            
            for match in matches:
                speaker = "1" if match.group(1) == "advisor" else "0"
                text = match.group(2).replace('\\"', '"').replace('\\n', ' ')
                lines.append({"speaker": speaker, "text": text})
            
            # If no matches found, try another pattern (sometimes LLMs format differently)
            if not lines:
                alt_pattern = r'("speaker"\s*:\s*"(advisor|client)"\s*,\s*"text"\s*:\s*"(.+?)")'
                matches = re.finditer(alt_pattern, llm_response, re.DOTALL)
                
                for match in matches:
                    speaker = "1" if match.group(2) == "advisor" else "0"
                    text = match.group(3).replace('\\"', '"').replace('\\n', ' ')
                    lines.append({"speaker": speaker, "text": text})
            
            # If still no matches, look for simple pattern
            if not lines:
                simple_pattern = r'(advisor|client):\s*"(.+?)"'
                matches = re.finditer(simple_pattern, llm_response, re.DOTALL)
                
                for match in matches:
                    speaker = "1" if match.group(1).lower() == "advisor" else "0"
                    text = match.group(2).strip()
                    lines.append({"speaker": speaker, "text": text})
        
        except Exception as e:
            logging.error(f"Error processing LLM response: {e}", exc_info=True)
        
        # Ensure there's at least one message from each participant
        if not any(line["speaker"] == "0" for line in lines):
            lines.append({"speaker": "0", "text": "Thank you for the information."})
            
        if not any(line["speaker"] == "1" for line in lines):
            lines.insert(0, {"speaker": "1", "text": "How can I help you today?"})
        
        return lines