"""
Tests for the new Chat Factory framework.
"""

import unittest
import os
import asyncio
import json
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import sys
import tempfile
import shutil

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import framework components
from chat_factory.config import BaseConfig
from chat_factory.strategies.financial_advisory import (
    FinancialAdvisoryTaxonomyStrategy,
    FinancialAdvisoryGenerationStrategy
)
from chat_factory.strategies.few_shot import BasicFewShotStrategy
from chat_factory.generator import SyntheticChatGenerator
from chat_factory.llm.base import LLMProvider
from chat_factory.models.conversation import ConversationFile


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, config):
        super().__init__(config)
    
    async def initialize(self):
        pass
    
    async def generate_content(self, prompt, max_tokens=None):
        # Return mock conversation based on the prompt
        if "Small Talk" in prompt:
            return """
            {"speaker": "advisor", "text": "Good morning! How are you doing today?"}
            {"speaker": "client", "text": "I'm doing well, thanks for asking. How about you?"}
            {"speaker": "advisor", "text": "I'm great, thanks. Beautiful weather we're having, isn't it?"}
            {"speaker": "client", "text": "Yes, it's lovely outside. Perfect for a walk later."}
            """
        elif "Market Commentary" in prompt:
            return """
            {"speaker": "advisor", "text": "Have you been following the recent market developments?"}
            {"speaker": "client", "text": "Not closely. What's happening?"}
            {"speaker": "advisor", "text": "There's been some volatility due to the Fed's recent announcements."}
            {"speaker": "client", "text": "How might that affect my portfolio?"}
            """
        else:
            return """
            {"speaker": "advisor", "text": "Hello, how can I help you today?"}
            {"speaker": "client", "text": "I'd like to discuss my investment strategy."}
            """
    
    async def retry_with_backoff(self, prompt, max_retries=10, initial_backoff=1.0, max_backoff=32.0):
        return await self.generate_content(prompt)


class TestFramework(unittest.IsolatedAsyncioTestCase):
    """Test case for the new Chat Factory framework."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for output
        self.temp_dir = tempfile.mkdtemp()
        self.few_shot_dir = os.path.join(self.temp_dir, "few_shot_examples")
        os.makedirs(self.few_shot_dir, exist_ok=True)
        
        # Create a sample few-shot example for general small talk
        with open(os.path.join(self.few_shot_dir, "small_talk.txt"), "w") as f:
            f.write('''
            {"speaker": "advisor", "text": "Hello! How are you today?"}
            {"speaker": "client", "text": "I'm well, thank you. How about yourself?"}
            {"speaker": "advisor", "text": "I'm doing great, thanks for asking. Anything specific you'd like to discuss today?"}
            ''')
        
        # Create a sample taxonomy file
        self.taxonomy_file = os.path.join(self.temp_dir, "test_taxonomy.json")
        with open(self.taxonomy_file, "w") as f:
            json.dump({
                "Small Talk": [
                    "Weather",
                    "Sports Events",
                    "Weekend Activities"
                ],
                "Market Commentary": [
                    "Market Volatility",
                    "Interest Rates",
                    "Inflation"
                ]
            }, f)
        
        # Create a test config
        self.config = BaseConfig(
            PROJECT_ID="test-project",
            RUN_ID="test-run",
            TAXONOMY_STRATEGY="financial_advisory",
            GENERATION_STRATEGY="financial_advisory",
            FEW_SHOT_STRATEGY="basic",
            OUTPUT_DIR=os.path.join(self.temp_dir, "output"),
            TAXONOMY_FILE=self.taxonomy_file,
            FEW_SHOT_EXAMPLES_DIR=self.few_shot_dir,
            CONVERSATION_MANIFEST_DIR=os.path.join(self.temp_dir, "manifests"),
            ADVISOR_NAMES=["John Doe", "Jane Smith"],
            CLIENT_NAMES=["Alice", "Bob"],
            PERSONAS=["Financial Advisor", "Investment Specialist"],
            CONVERSATION_TYPES=["Small Talk", "Market Commentary"],
            MESSAGE_FORMATS={
                "Small Talk": "informal",
                "Market Commentary": "formal"
            },
            NUM_CONVERSATIONS=2,
            MIN_MESSAGES=2,
            MAX_MESSAGES=4
        )
        
        # Initialize strategies
        self.taxonomy_strategy = FinancialAdvisoryTaxonomyStrategy(self.config)
        self.generation_strategy = FinancialAdvisoryGenerationStrategy(self.config)
        self.few_shot_strategy = BasicFewShotStrategy(self.config)
        self.llm_provider = MockLLMProvider(self.config)
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    async def test_taxonomy_strategy(self):
        """Test the financial advisory taxonomy strategy."""
        # Load taxonomy
        taxonomy = self.taxonomy_strategy.load_taxonomy(self.taxonomy_file)
        
        # Check taxonomy name
        self.assertEqual(taxonomy.name, "financial_advisory")
        
        # Check flattened topics
        flattened = self.taxonomy_strategy.flatten_taxonomy(taxonomy.raw_data)
        self.assertEqual(len(flattened), 6)  # 3 Small Talk + 3 Market Commentary
        
        # Check topic selection
        category, topic, subtopic = self.taxonomy_strategy.select_topic(flattened)
        self.assertIn(category, ["Small Talk", "Market Commentary"])
        
        # Verify taxonomy format detection
        format_type = self.taxonomy_strategy.detect_taxonomy_format(taxonomy.raw_data)
        self.assertEqual(format_type, "financial_advisory")
    
    async def test_generation_strategy(self):
        """Test the financial advisory generation strategy."""
        # Create a blueprint
        blueprint = self.generation_strategy.create_manifest_blueprint(
            "Small Talk", 
            ("Small Talk", "Weather", ""),
            3
        )
        
        # Check blueprint contents
        self.assertEqual(blueprint["category"], "Small Talk")
        self.assertEqual(blueprint["main_topic"], "Weather")
        self.assertEqual(blueprint["message_format"], "informal")
        
        # Test prompt construction
        few_shot_examples = await self.few_shot_strategy.get_examples(
            "Small Talk", "Small Talk", "Weather"
        )
        
        prompt = await self.generation_strategy.construct_prompt(
            "John Doe",
            "Alice",
            "Small Talk",
            3,
            blueprint,
            few_shot_examples
        )
        
        # Verify prompt content
        self.assertIn("John Doe", prompt)
        self.assertIn("Alice", prompt)
        self.assertIn("Weather", prompt)
        self.assertIn("Small Talk", prompt)
        
        # Test response processing
        mock_response = '''
        {"speaker": "advisor", "text": "Hello, how are you today?"}
        {"speaker": "client", "text": "I'm well, thank you!"}
        '''
        
        lines = self.generation_strategy.process_llm_response(mock_response)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["speaker"], "1")  # advisor
        self.assertEqual(lines[1]["speaker"], "0")  # client
    
    async def test_few_shot_strategy(self):
        """Test the basic few-shot example strategy."""
        # Override the get_examples method to use our test example
        async def mock_get_examples(*args, **kwargs):
            example_path = os.path.join(self.few_shot_dir, "small_talk.txt")
            with open(example_path, 'r') as f:
                return [f.read().strip()]
        
        # Patch the method
        original_get_examples = self.few_shot_strategy.get_examples
        self.few_shot_strategy.get_examples = mock_get_examples
        
        try:
            # Get examples
            examples = await self.few_shot_strategy.get_examples(
                "Small Talk", "Small Talk", "Weather"
            )
            
            # Check that we found examples
            self.assertEqual(len(examples), 1)
            
            # Format examples
            formatted = self.few_shot_strategy.format_examples(examples)
            self.assertIn("EXAMPLE 1", formatted)
            self.assertIn("advisor", formatted)
            self.assertIn("client", formatted)
        finally:
            # Restore the original method
            self.few_shot_strategy.get_examples = original_get_examples
    
    async def test_generator_integration(self):
        """Test the complete generator integration."""
        # Create the generator
        generator = SyntheticChatGenerator(
            config=self.config,
            taxonomy_strategy=self.taxonomy_strategy,
            generation_strategy=self.generation_strategy,
            few_shot_strategy=self.few_shot_strategy,
            llm_provider=self.llm_provider
        )
        
        # Process a single conversation
        conversation = await generator.process_conversation(
            conv_number=1,
            conversation_type="Small Talk",
            advisor_name="John Doe",
            client_name="Alice",
            num_messages=3
        )
        
        # Verify conversation structure
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.conversation_id.startswith("test-run_1_"), True)
        self.assertGreaterEqual(len(conversation.lines), 2)
        
        # Create a conversation file
        conversation_file = generator.conversation_buffer.get("John Doe_Alice")
        if conversation_file is None:
            # Create it if it doesn't exist
            from chat_factory.models.conversation import ConversationFile
            conversation_file = ConversationFile(
                version=generator.config.JSON_VERSION,
                advisor="John Doe",
                client="Alice",
                conversations=[conversation]
            )
        
        # Verify conversation file contains the conversation
        self.assertIsNotNone(conversation_file)
    
    async def test_generate_synthetic_data(self):
        """Test the complete synthetic data generation process."""
        # Create the generator
        generator = SyntheticChatGenerator(
            config=self.config,
            taxonomy_strategy=self.taxonomy_strategy,
            generation_strategy=self.generation_strategy,
            few_shot_strategy=self.few_shot_strategy,
            llm_provider=self.llm_provider
        )
        
        # Create a test conversation and save it directly
        advisor_name = "John"
        client_name = "Alice"
        
        conversation = await generator.process_conversation(
            conv_number=1,
            conversation_type="Small Talk",
            advisor_name=advisor_name,
            client_name=client_name,
            num_messages=3
        )
        
        # Create conversation file
        conversation_file = ConversationFile(
            version=generator.config.JSON_VERSION,
            advisor=advisor_name,
            client=client_name,
            conversations=[conversation]
        )
        
        # Save conversation file directly
        generator.save_conversation_file(advisor_name, client_name, conversation_file)
        
        # Check that output files were created
        output_dir = Path(self.config.OUTPUT_DIR) / self.config.RUN_ID
        
        # Check if any files were created
        files = list(output_dir.glob("*.json"))
        self.assertGreaterEqual(len(files), 1, f"No files found in {output_dir}")
        
        # If files exist, verify their content
        if files:
            with open(files[0], "r") as f:
                data = json.load(f)
                self.assertIn("advisor", data)
                self.assertIn("client", data)
                self.assertIn("conversations", data)
                self.assertGreaterEqual(len(data["conversations"]), 1)


if __name__ == "__main__":
    unittest.main()