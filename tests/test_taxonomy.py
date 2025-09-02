import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock, mock_open
import logging
from types import SimpleNamespace

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from main import SyntheticChatGenerator

class TestSyntheticChatGenerator(unittest.TestCase):
    """Test cases for the SyntheticChatGenerator class, focusing on taxonomy handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Sample taxonomy for testing
        self.test_taxonomy = {
            "Business/Advisory": {
                "Financial Goals & Planning": [
                    "Retirement Goals",
                    "Investment Goals",
                    "Education Planning"
                ],
                "Ultra High Net Worth Specifics": [
                    "Wealth Preservation",
                    "Complex Investments"
                ]
            },
            "Small Talk": [
                "Weather",
                "Sports Events",
                "Weekend Activities"
            ],
            "Product & Service Inquiry": {
                "Investment Products": [
                    "Stocks",
                    "Bonds",
                    "ETFs"
                ]
            }
        }
        
        # Company tagging taxonomy for testing
        self.company_tagging_taxonomy = {
            "conversation_types": {
                "Trade Discussions": {
                    "company_count_options": [1, 2, 3]
                },
                "Deal Negotiations": {
                    "company_count_options": [2, 3]
                },
                "Stock Analysis": {
                    "company_count_options": [1]
                }
            }
        }
        
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
            PROJECT_ID="test-project",
            LOCATION="us-central1",
            MODEL_NAME="gemini-1.5-flash",
            TEMPERATURE=0.3,
            TOP_P=1,
            TOP_K=40
        )
        
    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    def test_flatten_taxonomy_hierarchical(self, mock_file_handler, mock_makedirs, mock_load_taxonomy):
        """Test flattening a hierarchical taxonomy correctly preserves all levels"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_file_handler.return_value = MagicMock()
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.taxonomy = self.test_taxonomy
        
        # Act
        flattened = generator.flatten_taxonomy(self.test_taxonomy)
        
        # Assert
        self.assertEqual(len(flattened), 11)  # Total number of leaf nodes in our test taxonomy
        
        # Check that hierarchical categories are properly flattened
        business_retirement = ("Business/Advisory", "Financial Goals & Planning", "Retirement Goals")
        self.assertIn(business_retirement, flattened)
        
        # Check that flat categories are properly flattened with empty subtopic
        small_talk_weather = ("Small Talk", "Weather", "")
        self.assertIn(small_talk_weather, flattened)

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    def test_flatten_taxonomy_company_tagging(self, mock_file_handler, mock_makedirs, mock_load_taxonomy):
        """Test flattening a company tagging taxonomy"""
        # Arrange
        mock_load_taxonomy.return_value = self.company_tagging_taxonomy
        mock_file_handler.return_value = MagicMock()
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.taxonomy = self.company_tagging_taxonomy
        
        # Act
        flattened = generator.flatten_taxonomy(self.company_tagging_taxonomy)
        
        # Assert
        self.assertEqual(len(flattened), 3)  # Three conversation types
        
        # Check that conversation types are used as both category and topic
        trade_discussions = ("Trade Discussions", "Trade Discussions", "")
        self.assertIn(trade_discussions, flattened)

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    @patch('random.choice')
    def test_select_topic(self, mock_random_choice, mock_file_handler, mock_makedirs, mock_load_taxonomy):
        """Test selecting a topic from the flattened taxonomy"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_file_handler.return_value = MagicMock()
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.taxonomy = self.test_taxonomy
        generator.flattened_topics = generator.flatten_taxonomy(self.test_taxonomy)
        
        # Mock random.choice to return a specific tuple
        expected_tuple = ("Business/Advisory", "Financial Goals & Planning", "Retirement Goals")
        mock_random_choice.return_value = expected_tuple
        
        # Act
        category, topic, subtopic = generator.select_topic()
        
        # Assert
        self.assertEqual(category, "Business/Advisory")
        self.assertEqual(topic, "Financial Goals & Planning")
        self.assertEqual(subtopic, "Retirement Goals")

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.SyntheticChatGenerator.load_company_data')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    def test_create_manifest_blueprint_with_topics(self, mock_file_handler, mock_makedirs, mock_load_company_data, mock_load_taxonomy):
        """Test creating a manifest blueprint with category and topic information"""
        # Arrange
        mock_load_taxonomy.return_value = self.test_taxonomy
        mock_load_company_data.return_value = []
        mock_file_handler.return_value = MagicMock()
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.taxonomy = self.test_taxonomy
        generator.flattened_topics = generator.flatten_taxonomy(self.test_taxonomy)
        generator.company_targeting = {
            "enabled": True,
            "probability": 0.8,
            "min_companies": 1,
            "max_companies": 3
        }
        
        # Act
        manifest = generator.create_manifest_blueprint(
            "Financial Advisory", 
            5, 
            category="Business/Advisory",
            topic="Financial Goals & Planning.Retirement Goals"
        )
        
        # Assert
        self.assertEqual(manifest["category"], "Business/Advisory")
        self.assertEqual(manifest["topic"], "Financial Goals & Planning.Retirement Goals")

    @patch('main.SyntheticChatGenerator._load_taxonomy')
    @patch('main.os.makedirs')
    @patch('main.logging.FileHandler')
    def test_select_company_count_from_taxonomy(self, mock_file_handler, mock_makedirs, mock_load_taxonomy):
        """Test selecting company count from the taxonomy for a specific conversation type"""
        # Arrange
        mock_load_taxonomy.return_value = self.company_tagging_taxonomy
        mock_file_handler.return_value = MagicMock()
        generator = SyntheticChatGenerator(config=self.mock_config)
        generator.taxonomy = self.company_tagging_taxonomy
        generator.taxonomy_format = "company_tagging"
        generator.conversation_type_metadata = {
            "Trade Discussions": {
                "company_count_options": [1, 2, 3]
            },
            "Deal Negotiations": {
                "company_count_options": [2, 3]
            },
            "Stock Analysis": {
                "company_count_options": [1]
            }
        }
        
        # Act - with a type that has company_count_options
        with patch('random.choice', return_value=2) as mock_choice:
            count = generator.select_company_count("Trade Discussions")
            # Assert
            self.assertEqual(count, 2)
            mock_choice.assert_called_with([1, 2, 3])
        
        # Act - with a type that doesn't have company_count_options
        with patch('random.randint', return_value=2) as mock_randint:
            count = generator.select_company_count("Unknown Type")
            # Assert
            self.assertEqual(count, 2)
            mock_randint.assert_called_with(1, 3)


if __name__ == '__main__':
    unittest.main()
