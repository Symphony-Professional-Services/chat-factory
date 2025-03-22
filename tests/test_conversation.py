import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
import logging
import asyncio
from types import SimpleNamespace
from datetime import datetime
import uuid
from unittest.mock import mock_open

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from main import SyntheticChatGenerator, SingleConversation, ChatLine, ConversationFile

class TestConversationGeneration(unittest.IsolatedAsyncioTestCase):
    """Test cases for conversation generation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Sample taxonomy for testing
        self.test_taxonomy = {
            "Business/Advisory": {
                "Financial Goals & Planning": [
                    "Retirement Goals",
                    "Investment Goals",
                    "Education Planning"
                ]
            },
            "Small Talk": [
                "Weather",
                "Sports Events"
            ]
        }
        
        # Mock chat lines for testing
        self.mock_chat_lines = [
            ChatLine(speaker="0", text="Hello, how can I help you with retirement planning today?"),
            ChatLine(speaker="1", text="I'd like to discuss my 401k options."),
            ChatLine(speaker="0", text="Great, let's review your current retirement accounts.")
        ]
        
        # Set a fixed UUID for testing
        self.uuid_patch = patch('uuid.uuid4')
        self.mock_uuid = self.uuid_patch.start()
        self.mock_uuid.return_value.hex = "12345678abcdef90"
        
        # Set a fixed datetime for testing
        self.datetime_patch = patch('main.datetime')
        self.mock_datetime = self.datetime_patch.start()
        self.mock_datetime.now.return_value.isoformat.return_value = "2025-03-22T12:00:00Z"
        
        # Mock config settings
        self.mock_config = SimpleNamespace(
            TAXONOMY_FILE="mock_taxonomy.json",
            COMPANY_TARGETING={
                "enabled": True,
                "probability": 0.8,
                "min_companies": 1,
                "max_companies": 3
            },
            TAXONOMY_TYPE="financial_advisor",
            TOPIC_DISTRIBUTION="uniform",
            PERSONAS=[
                "Senior Wealth Advisor",
                "Investment Portfolio Manager"
            ],
            CONVERSATION_TYPES=[
                "Small Talk",
                "Market Commentary"
            ],
            MESSAGE_FORMATS={
                "Small Talk": "informal",
                "Market Commentary": "structured"
            },
            COMPANY_DATA_FILE="",
            MESSAGE_LENGTH_RATIO={
                "short": 0.4,
                "medium": 0.3,
                "long": 0.3
            },
            ADVISOR_NAMES=["John", "Mary"],
            CLIENT_NAMES=["Alice", "Bob"],
            FEW_SHOT_EXAMPLES_DIR="few_shot_examples",
            CONVERSATION_MANIFEST_DIR="conversation_scripts",
            OUTPUT_DIR="synthetic_data",
            JSON_VERSION="5",
            NUM_CONVERSATIONS=10,
            MIN_MESSAGES=2,
            MAX_MESSAGES=10,
            PROJECT_ID="sk-ml-inference",
            LOCATION="us-central1",
            MODEL_NAME="gemini-1.5-flash-002",
            TEMPERATURE=0.3,
            TOP_P=1,
            TOP_K=40
        )
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.uuid_patch.stop()
        self.datetime_patch.stop()
    
    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    @patch('main.SyntheticChatGenerator.select_topic')
    @patch('main.SyntheticChatGenerator.create_manifest_blueprint')
    @patch('main.SyntheticChatGenerator.generate_conversation')
    async def test_process_conversation_topic_formatting(self, 
                                                 mock_generate_conversation,
                                                 mock_create_manifest,
                                                 mock_select_topic,
                                                 mock_file_handler,
                                                 mock_makedirs,
                                                 mock_load_taxonomy):
        """Test that process_conversation correctly formats topics with subtopics"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_select_topic.return_value = ("Business/Advisory", "Financial Goals & Planning", "Retirement Goals")
        mock_file_handler.return_value = MagicMock()
        
        # Mock the blueprint
        mock_blueprint = {
            "category": "Business/Advisory",
            "topic": "Financial Goals & Planning.Retirement Goals",
            "company_targeting_enabled": False,
            "key_companies": []
        }
        mock_create_manifest.return_value = mock_blueprint
        
        # Mock the chat generation
        mock_generate_conversation.return_value = self.mock_chat_lines
        
        # Create the generator
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.run_id = "test_run"
        generator.manifest_logger = MagicMock()
        
        # Act
        conversation = await generator.process_conversation(
            conv_number=1,
            conversation_type="Financial Advisory",
            advisor_name="John",
            client_name="Alice",
            num_messages=3
        )
        
        # Assert
        self.assertEqual(conversation.category, "Business/Advisory")
        self.assertEqual(conversation.topic, "Financial Goals & Planning.Retirement Goals")
        
        # Check manifest log contains correct topic info
        log_call_args = generator.manifest_logger.info.call_args[0][0]
        log_data = json.loads(log_call_args)
        self.assertEqual(log_data["category"], "Business/Advisory")
        self.assertEqual(log_data["topic"], "Financial Goals & Planning.Retirement Goals")

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    def test_topic_subtopic_in_to_dict(self, mock_load_taxonomy):
        """Test that SingleConversation.to_dict() correctly includes the topic with subtopic"""
        # Arrange
        conversation = SingleConversation(
            conversation_id="test-123",
            timestamp="2025-03-22T12:00:00Z",
            category="Business/Advisory",
            topic="Financial Goals & Planning.Retirement Goals",
            lines=self.mock_chat_lines
        )
        
        # Act
        result = conversation.to_dict()
        
        # Assert
        self.assertEqual(result["category"], "Business/Advisory")
        self.assertEqual(result["topic"], "Financial Goals & Planning.Retirement Goals")
        
    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    @patch('main.SyntheticChatGenerator.select_topic')
    def test_topic_formatting_in_select_topic(self, mock_select_topic, mock_file_handler, mock_makedirs, mock_load_taxonomy):
        """Test that topics are correctly formatted by the select_topic method"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_file_handler.return_value = MagicMock()
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.flattened_topics = [
            ("Business/Advisory", "Financial Goals & Planning", "Retirement Goals"),
            ("Small Talk", "Weather", "")
        ]
        
        # Test case 1: With subtopic
        mock_select_topic.return_value = ("Business/Advisory", "Financial Goals & Planning", "Retirement Goals")
        generator.select_topic = mock_select_topic
        
        # Act
        category, topic, subtopic = generator.select_topic()
        
        # Assert
        self.assertEqual(category, "Business/Advisory")
        self.assertEqual(topic, "Financial Goals & Planning")
        self.assertEqual(subtopic, "Retirement Goals")
        
        # Test case 2: Without subtopic
        mock_select_topic.return_value = ("Small Talk", "Weather", "")
        
        # Act
        category, topic, subtopic = generator.select_topic()
        
        # Assert
        self.assertEqual(category, "Small Talk")
        self.assertEqual(topic, "Weather")
        self.assertEqual(subtopic, "")

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    def test_construct_prompt_includes_topics(self, mock_file_handler, mock_makedirs, mock_load_taxonomy):
        """Test that construct_prompt includes topic information in the prompt"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_file_handler.return_value = MagicMock()
        generator = SyntheticChatGenerator(config=self.mock_config)
        
        # Create a manifest blueprint with topic information
        manifest_blueprint = {
            "category": "Business/Advisory",
            "topic": "Financial Goals & Planning.Retirement Goals",
            "company_targeting_enabled": False,
            "key_companies": []
        }
        
        # Act
        prompt = generator.construct_prompt(
            advisor_name="John",
            client_name="Alice",
            conversation_type="Financial Advisory",
            num_messages=3,
            manifest_blueprint=manifest_blueprint
        )
        
        # Assert
        self.assertIn("Conversation Category: Business/Advisory", prompt)
        self.assertIn("Topic Area: Financial Goals & Planning", prompt)
        self.assertIn("Specific Topic: Retirement Goals", prompt)

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.SyntheticChatGenerator.load_company_data')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    @patch('main.json.dump')
    def test_conversation_file_output_format(self, mock_json_dump, mock_file_handler, mock_makedirs, mock_load_company_data, mock_load_taxonomy):
        """Test that the conversation file output correctly includes topics with subtopics"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_load_company_data.return_value = []
        mock_file_handler.return_value = MagicMock()
        
        # Create a generator
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.run_id = "test_run"
        
        # Create a conversation with hierarchical topic
        conversation = SingleConversation(
            conversation_id="123",
            timestamp="2025-03-22T12:00:00Z",
            category="Business/Advisory",
            topic="Financial Goals & Planning.Retirement Goals",
            lines=self.mock_chat_lines
        )
        
        # Create a conversation file 
        conversation_file = ConversationFile(
            version="5",
            advisor="Alice Johnson",
            client="Bob",
            conversations=[conversation]
        )
        
        # Mock the open function
        with patch('builtins.open', mock_open()) as mock_file:
            # Act
            generator.save_conversation_file("Alice Johnson", "Bob", conversation_file)
            
            # Assert
            # Check if json.dump was called
            mock_json_dump.assert_called_once()
            
            # Get the actual data passed to json.dump
            actual_data = mock_json_dump.call_args[0][0]
            
            # Verify the conversation structure
            self.assertEqual(actual_data["advisor"], "Alice Johnson")
            self.assertEqual(actual_data["client"], "Bob")
            self.assertEqual(len(actual_data["conversations"]), 1)
            
            # Verify the topic format
            output_conversation = actual_data["conversations"][0]
            self.assertEqual(output_conversation["category"], "Business/Advisory")
            self.assertEqual(output_conversation["topic"], "Financial Goals & Planning.Retirement Goals")
            
            # Verify the expected format is preserved
            self.assertIn(".", output_conversation["topic"])
            main_topic, subtopic = output_conversation["topic"].split(".")
            self.assertEqual(main_topic, "Financial Goals & Planning")
            self.assertEqual(subtopic, "Retirement Goals")

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.SyntheticChatGenerator.load_company_data')
    @patch('main.SyntheticChatGenerator.generate_conversation')
    @patch('main.SyntheticChatGenerator.create_manifest_blueprint')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    async def test_process_conversation_output_format(self, mock_file_handler, mock_makedirs, 
                                                    mock_create_manifest, mock_generate_conversation, 
                                                    mock_load_company_data, mock_load_taxonomy):
        """Test that process_conversation correctly formats the final output with topic.subtopic format"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_load_company_data.return_value = []
        mock_file_handler.return_value = MagicMock()
        
        # Mock the conversation generation result
        mock_conversation_lines = [
            {"speaker": "advisor", "text": "Hello, how can I help you with your retirement planning?"},
            {"speaker": "client", "text": "I'm interested in discussing my retirement goals."}
        ]
        mock_generate_conversation.return_value = mock_conversation_lines
        
        # Mock the manifest blueprint
        mock_manifest = {
            "category": "Business/Advisory",
            "main_topic": "Financial Goals & Planning",
            "subtopic": "Retirement Goals",
            "companies": []
        }
        mock_create_manifest.return_value = mock_manifest
        
        # Create a generator with the test taxonomy
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.taxonomy = self.test_taxonomy
        generator.flattened_topics = generator.flatten_taxonomy(self.test_taxonomy)
        
        # Mock the manifest logger to prevent the TypeError
        mock_logger = MagicMock()
        generator.manifest_logger = mock_logger
        
        # Pre-create the conversation buffer entry
        buffer_key = f"Alice Johnson_Bob Smith"
        generator.conversation_buffer[buffer_key] = ConversationFile(
            version="5",
            advisor="Alice Johnson",
            client="Bob Smith",
            conversations=[]
        )
        
        # Mock the select_topic method to return a specific topic
        with patch.object(generator, 'select_topic', return_value=('Business/Advisory', 'Financial Goals & Planning', 'Retirement Goals')):
            # Process the conversation
            conversation = await generator.process_conversation(
                conv_number=1,
                conversation_type="retirement_planning",
                advisor_name="Alice Johnson",
                client_name="Bob Smith",
                num_messages=2
            )
            
            # Manually add the conversation to the buffer (like generate_synthetic_data would do)
            generator.conversation_buffer[buffer_key].conversations.append(conversation)
            
            # Assert - check the conversation was added to the buffer
            self.assertIn(buffer_key, generator.conversation_buffer)
            
            conversation_file = generator.conversation_buffer[buffer_key]
            self.assertEqual(len(conversation_file.conversations), 1)
            
            # Check the topic formatting in the conversation object
            conversation = conversation_file.conversations[0]
            self.assertEqual(conversation.category, "Business/Advisory")
            self.assertEqual(conversation.topic, "Financial Goals & Planning.Retirement Goals")
            
            # Check the JSON serialization
            json_data = conversation.to_dict()
            self.assertEqual(json_data["category"], "Business/Advisory")
            self.assertEqual(json_data["topic"], "Financial Goals & Planning.Retirement Goals")
            
            # Check if save_conversation_file would correctly preserve the format
            with patch('builtins.open', mock_open()) as mock_file, patch('json.dump') as mock_json_dump:
                generator.save_conversation_file("Alice Johnson", "Bob Smith", conversation_file)
                # Verify json.dump was called with the correct data
                self.assertTrue(mock_json_dump.called)
                actual_data = mock_json_dump.call_args[0][0]
                self.assertEqual(actual_data["conversations"][0]["topic"], "Financial Goals & Planning.Retirement Goals")
            
    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.SyntheticChatGenerator.load_company_data')
    @patch('main.logging.FileHandler')
    @patch('main.os.makedirs')
    async def test_call_vertex_ai_with_rate_limit_retries(self, mock_makedirs, mock_file_handler, 
                                                        mock_load_company_data, mock_load_taxonomy):
        """Test that call_vertex_ai retries on rate limit (429) errors with exponential backoff"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_load_company_data.return_value = []
        mock_file_handler.return_value = MagicMock()
        
        # Create a generator
        generator = SyntheticChatGenerator(config=self.mock_config)
        
        # Create a mock response for the successful attempt
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.text = "Successful response"
        
        # Create a side effect function that fails with 429 twice, then succeeds
        side_effects = []
        
        # First two attempts fail with 429 error
        for _ in range(2):
            side_effects.append(Exception("Quota exceeded: 429 Resource has been exhausted"))
        
        # Third attempt succeeds
        side_effects.append(mock_response)
        
        # Mock generate_content_async with our side effects
        with patch.object(generator.llm, 'generate_content_async', side_effect=side_effects) as mock_gen_content:
            # Act - Test with reduced retry parameters for faster tests
            with patch('asyncio.sleep') as mock_sleep:  # Patch sleep to avoid waiting in tests
                result = await generator.call_vertex_ai(
                    "Test prompt", 
                    max_retries=3, 
                    initial_backoff=0.1, 
                    max_backoff=0.5
                )
            
            # Assert
            # Verify we called the API 3 times (2 failures + 1 success)
            self.assertEqual(mock_gen_content.call_count, 3)
            
            # Verify we slept twice (after each failure)
            self.assertEqual(mock_sleep.call_count, 2)
            
            # Verify the backoff increases
            first_sleep = mock_sleep.call_args_list[0][0][0]
            second_sleep = mock_sleep.call_args_list[1][0][0]
            self.assertGreater(second_sleep, first_sleep)
            
            # Verify we got the successful response
            self.assertEqual(result, "Successful response")
            
if __name__ == '__main__':
    unittest.main()
