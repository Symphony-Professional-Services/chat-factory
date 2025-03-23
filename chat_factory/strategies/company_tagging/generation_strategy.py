"""
Generation strategy for company tagging use case.
"""

import re
import json
import logging
import random
import csv
from typing import List, Dict, Any, Tuple, Optional
import asyncio

from ..base import GenerationStrategy


class CompanyTaggingGenerationStrategy(GenerationStrategy):
    """
    Implementation of generation strategy for company tagging conversations.
    
    This strategy specializes in creating conversations that prominently feature
    company mentions for training company entity extraction models.
    """
    
    def __init__(self, config):
        """
        Initialize the company tagging generation strategy.
        
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
        
        # Company targeting is required for this strategy
        self.company_targeting = getattr(config, 'COMPANY_TARGETING', {
            "enabled": True,
            "probability": 1.0,  # Always include companies in company tagging use case
            "min_companies": 1,
            "max_companies": 3
        })
        
        # Always enable company targeting for this strategy
        if not self.company_targeting.get("enabled", False):
            self.company_targeting["enabled"] = True
            logging.info("Enabling company targeting for CompanyTaggingGenerationStrategy")
        
        # Set higher probability for company tagging
        self.company_targeting["probability"] = 1.0
        
        # Load company data
        self.company_data = []
        self._load_company_data()
    
    def _load_company_data(self):
        """Load company data from file."""
        company_data_file = getattr(self.config, 'COMPANY_DATA_FILE', '')
        if not company_data_file:
            logging.warning("Company data file path is empty. Cannot load company data.")
            return
        
        try:
            with open(company_data_file, 'r') as file:
                reader = csv.DictReader(file)
                self.company_data = list(reader)
            logging.info(f"Loaded {len(self.company_data)} companies from {company_data_file}")
        except Exception as e:
            logging.error(f"Error loading company data file: {e}")
            
            # Create some sample company data as a fallback
            logging.warning("Using fallback sample company data")
            self.company_data = [
                {"name": "Acme Corp", "ticker": "ACME", "industry": "Technology"},
                {"name": "Globex", "ticker": "GBX", "industry": "Manufacturing"},
                {"name": "Stark Industries", "ticker": "STRK", "industry": "Defense"},
                {"name": "Wayne Enterprises", "ticker": "WNTR", "industry": "Conglomerate"},
                {"name": "Oscorp", "ticker": "OSC", "industry": "Pharmaceuticals"}
            ]
    
    def create_manifest_blueprint(self, conversation_type: str, topic: Tuple[str, str, str], 
                                 num_messages: int) -> Dict[str, Any]:
        """
        Create a manifest blueprint for a company tagging conversation.
        
        Args:
            conversation_type: Type of conversation to generate
            topic: Selected topic as (category, topic, subtopic)
            num_messages: Number of messages to generate
            
        Returns:
            Dictionary containing blueprint for conversation generation
        """
        category, main_topic, subtopic = topic
        
        # Company targeting logic
        key_companies = []
        company_targeting_enabled = False
        
        if self.company_data and random.random() < self.company_targeting.get("probability", 1.0):
            company_targeting_enabled = True
            
            # Select number of companies to include
            min_companies = self.company_targeting.get("min_companies", 1)
            max_companies = self.company_targeting.get("max_companies", 3)
            num_companies = random.randint(min_companies, max_companies)
            
            # Select random companies
            if len(self.company_data) >= num_companies:
                selected_companies = random.sample(self.company_data, num_companies)
                key_companies = []
                
                # Process each selected company with its variations
                for company in selected_companies:
                    # Always add the primary name
                    key_companies.append(company.get('name', ''))
                    
                    # Sometimes add ticker
                    if company.get('ticker') and random.random() > 0.3:
                        key_companies.append(company.get('ticker', ''))
                    
                    # Sometimes add formal name if different from primary name
                    if company.get('formal_name') and company.get('formal_name') != company.get('name') and random.random() > 0.7:
                        key_companies.append(company.get('formal_name', ''))
                    
                    # Sometimes add variations with lower probability
                    if company.get('variations'):
                        variations = company.get('variations', '').split(';')
                        for variation in variations:
                            if variation.strip() and random.random() > 0.8:
                                key_companies.append(variation.strip())
                    
                    # Occasionally add misspellings with even lower probability
                    if company.get('misspellings'):
                        misspellings = company.get('misspellings', '').split(';')
                        for misspelling in misspellings:
                            if misspelling.strip() and random.random() > 0.9:
                                key_companies.append(misspelling.strip())
        
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
            "message_style": self._get_message_style(message_format, conversation_type),
            "typical_message_length": self._get_message_length_distribution(conversation_length)
        }
        
        logging.info(f"Created company tagging manifest blueprint with {len(key_companies)} companies")
        return blueprint
    
    def _get_message_style(self, message_format: str, conversation_type: str) -> str:
        """
        Get appropriate message style based on format and conversation type.
        
        Args:
            message_format: Format of the message (formal, informal, etc.)
            conversation_type: Type of conversation
            
        Returns:
            Description of message style
        """
        # Custom styles based on conversation type
        type_styles = {
            "Trade discussions": "direct, actionable, focused on timing and opportunity",
            "Deal negotiations": "persuasive, specific, detail-oriented, monetary focus",
            "Stock analysis": "analytical, data-driven, evaluative, predictive",
            "Market updates": "informative, current, trend-focused, comparative",
            "News on specific companies": "factual, timely, specific, impact-oriented",
            "Earnings reports discussions": "numerical, performance-oriented, comparative to expectations"
        }
        
        # If we have a style for this conversation type, use it
        if conversation_type in type_styles:
            return type_styles[conversation_type]
        
        # Otherwise fall back to format-based styles
        format_styles = {
            "formal": "professional, structured, detailed, uses industry terminology",
            "informal": "conversational, friendly, uses simpler language",
            "confidential": "discreet, careful, sensitive, focused on privacy",
            "structured": "organized, analytical, fact-based, methodical"
        }
        return format_styles.get(message_format, "professional, clear, helpful")
    
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
        Construct a prompt for company tagging conversation generation.
        
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
        message_style = manifest_blueprint["message_style"]
        
        # Select a random persona for the advisor
        persona = random.choice(self.personas) if self.personas else "Financial Analyst"
        
        # Build the prompt
        prompt = f"""You are a conversation generator AI that creates realistic synthetic conversations between a financial professional and their client about companies and markets.

Generate a conversation between {advisor_name} (a {persona}) and their client {client_name}.

Conversation Category: {category}
Topic Area: {main_topic}"""

        if subtopic:
            prompt += f"\nSpecific Topic: {subtopic}"
        
        prompt += f"""
Conversation Type: {conversation_type}
Message Format: {message_format}
Message Style: {message_style}
Number of Messages: {num_messages}

The conversation should focus on financial markets and company-specific information, discussing corporate news, stock performance, and investment opportunities related to specific companies.
"""

        # Company targeting instructions - always include for this strategy
        if company_targeting_enabled and key_companies:
            # Group companies by their base name to identify variations
            company_groups = {}
            for item in key_companies:
                # Simple heuristic: shorter names that appear within longer ones
                # are likely variations/tickers of the same company
                assigned = False
                for base_name in company_groups.keys():
                    # Ignore very short items (like 1-2 chars) to avoid false matches
                    if len(item) <= 2:
                        if item.upper() in company_groups:
                            company_groups[item.upper()].append(item)
                            assigned = True
                            break
                    elif base_name in item or item in base_name:
                        company_groups[base_name].append(item)
                        assigned = True
                        break
                
                if not assigned:
                    company_groups[item] = [item]
            
            # Create a readable format of the companies with variations
            company_display = []
            for base_name, variations in company_groups.items():
                if len(variations) > 1:
                    company_display.append(f"{base_name} (also referred to as: {', '.join(v for v in variations if v != base_name)})")
                else:
                    company_display.append(base_name)
            
            prompt += f"""
During the conversation, prominently feature and discuss the following companies:
{', '.join(company_display)}

IMPORTANT INSTRUCTIONS FOR COMPANY MENTIONS:
1. Each company should be mentioned at least twice in the conversation
2. Use a variety of ways to refer to the same company - sometimes formal name, sometimes ticker, 
   sometimes abbreviations as shown in the company list above
3. Discuss specific aspects of these companies such as:
   - Recent financial performance
   - Market position
   - Product announcements
   - Leadership changes
   - Stock price movements
   - Competitive position
4. Make the company mentions natural and relevant to the conversation topic
5. Some companies should be discussed in detail while others might be mentioned for comparison
6. When referring to tickers, sometimes use formats like: AAPL, $AAPL, or Apple (AAPL)
"""
        else:
            # Fallback if no companies were provided
            prompt += """
During the conversation, naturally incorporate mentions of at least 2-3 relevant companies in the discussion.
Choose companies that would be appropriate for the conversation topic and discuss aspects like:
- Recent financial performance
- Market position
- Product announcements
- Leadership changes
- Stock price movements
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
            lines.append({"speaker": "0", "text": "Thank you for the information about these companies."})
            
        if not any(line["speaker"] == "1" for line in lines):
            lines.insert(0, {"speaker": "1", "text": "Let's discuss some interesting companies in the market today."})
        
        return lines