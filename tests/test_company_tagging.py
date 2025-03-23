"""
Unit tests for company tagging strategies.
"""

import unittest
import tempfile
import json
import csv
import os
import random
from unittest.mock import patch, MagicMock
import asyncio

from chat_factory.strategies.company_tagging import (
    CompanyTaggingTaxonomyStrategy,
    CompanyTaggingGenerationStrategy
)
from chat_factory.models.taxonomy import Taxonomy


class TestCompanyTaggingTaxonomyStrategy(unittest.TestCase):
    """Test cases for the CompanyTaggingTaxonomyStrategy class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock config
        self.config = MagicMock()
        self.config.TOPIC_DISTRIBUTION = "uniform"
        
        # Create a temporary taxonomy file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.taxonomy_file = os.path.join(self.temp_dir.name, "taxonomy.json")
        
        self.taxonomy_data = {
            "Market Commentary": [
                "Recent Market Performance",
                "Analysis of Interest Rate Changes"
            ],
            "Stock Analysis": [
                "Fundamental Analysis",
                "Technical Analysis"
            ],
            "conversation_types": {
                "Trade discussions": {
                    "description": "Trade focused conversations",
                    "company_tagging": {
                        "enabled": True,
                        "company_count_options": [2, 3]
                    }
                }
            }
        }
        
        with open(self.taxonomy_file, 'w') as f:
            json.dump(self.taxonomy_data, f)
        
        # Create the strategy
        self.strategy = CompanyTaggingTaxonomyStrategy(self.config)
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_load_taxonomy(self):
        """Test loading taxonomy file."""
        taxonomy = self.strategy.load_taxonomy(self.taxonomy_file)
        
        self.assertEqual(taxonomy.name, "company_tagging")
        self.assertEqual(len(taxonomy.topics), 4)  # 2 topics x 2 subtopics
        self.assertEqual(len(taxonomy.conversation_types), 1)
        self.assertTrue(taxonomy.conversation_types["Trade discussions"].company_tagging.enabled)
    
    def test_detect_taxonomy_format(self):
        """Test detecting taxonomy format."""
        format_type = self.strategy.detect_taxonomy_format(self.taxonomy_data)
        self.assertEqual(format_type, "company_tagging")
        
        # Test with financial advisory format
        financial_data = {"Category": {"Topic": ["Subtopic"]}}
        format_type = self.strategy.detect_taxonomy_format(financial_data)
        self.assertEqual(format_type, "financial_advisory")
    
    def test_flatten_taxonomy(self):
        """Test flattening taxonomy."""
        flattened = self.strategy.flatten_taxonomy(self.taxonomy_data)
        
        # Should have 4 flattened entries (2 categories x 2 topics each)
        self.assertEqual(len(flattened), 4)
        
        # conversation_types should be skipped
        for category, topic, subtopic in flattened:
            self.assertNotEqual(category, "conversation_types")


class TestCompanyTaggingGenerationStrategy(unittest.IsolatedAsyncioTestCase):
    """Test cases for the CompanyTaggingGenerationStrategy class."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        # Create a mock config
        self.config = MagicMock()
        self.config.PERSONAS = ["Analyst", "Advisor"]
        self.config.MESSAGE_FORMATS = {"Trade discussions": "informal"}
        self.config.MESSAGE_LENGTH_RATIO = {"short": 0.4, "medium": 0.3, "long": 0.3}
        self.config.COMPANY_TARGETING = {"enabled": True, "probability": 1.0, "min_companies": 1, "max_companies": 3}
        
        # Create a temporary company data file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.company_file = os.path.join(self.temp_dir.name, "companies.csv")
        
        with open(self.company_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "ticker", "sector", "variations", "misspellings", "formal_name"])
            writer.writerow(["Apple", "AAPL", "Technology", "Apple Inc;APPL", "Aple;Appel", "Apple Inc."])
            writer.writerow(["Microsoft", "MSFT", "Technology", "MSFT;MS", "Microsft;Microsfot", "Microsoft Corporation"])
        
        self.config.COMPANY_DATA_FILE = self.company_file
        
        # Create the strategy
        self.strategy = CompanyTaggingGenerationStrategy(self.config)
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_load_company_data(self):
        """Test loading company data."""
        self.assertEqual(len(self.strategy.company_data), 2)
        self.assertEqual(self.strategy.company_data[0]["name"], "Apple")
        self.assertEqual(self.strategy.company_data[1]["ticker"], "MSFT")
    
    def test_create_manifest_blueprint(self):
        """Test creating manifest blueprint."""
        # Ensure company data is loaded
        with open(self.company_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "ticker", "sector", "variations", "misspellings", "formal_name"])
            writer.writerow(["Apple", "AAPL", "Technology", "Apple Inc;APPL", "Aple;Appel", "Apple Inc."])
            writer.writerow(["Microsoft", "MSFT", "Technology", "MSFT;MS", "Microsft;Microsfot", "Microsoft Corporation"])
        
        # Force reload company data
        self.strategy._load_company_data()
        
        # Set random seed for deterministic company selection
        random.seed(42)
        
        topic = ("Market Commentary", "Recent Market Performance", "")
        blueprint = self.strategy.create_manifest_blueprint("Trade discussions", topic, 6)
        
        self.assertEqual(blueprint["category"], "Market Commentary")
        self.assertEqual(blueprint["main_topic"], "Recent Market Performance")
        self.assertEqual(blueprint["conversation_type"], "Trade discussions")
        self.assertEqual(blueprint["message_format"], "informal")
        self.assertTrue(blueprint["company_targeting_enabled"])
        self.assertGreaterEqual(len(blueprint["key_companies"]), 1)
    
    async def test_construct_prompt(self):
        """Test constructing prompt."""
        manifest_blueprint = {
            "category": "Market Commentary",
            "main_topic": "Recent Market Performance",
            "subtopic": "",
            "conversation_type": "Trade discussions",
            "message_format": "informal",
            "conversation_length": "medium",
            "company_targeting_enabled": True,
            "key_companies": ["Apple", "AAPL", "Microsoft"],
            "message_style": "conversational, friendly",
            "typical_message_length": {"short": 0.4, "medium": 0.3, "long": 0.3}
        }
        
        prompt = await self.strategy.construct_prompt(
            "Alice", "Bob", "Trade discussions", 6, manifest_blueprint, []
        )
        
        self.assertIn("Alice", prompt)
        self.assertIn("Bob", prompt)
        self.assertIn("Market Commentary", prompt)
        self.assertIn("Recent Market Performance", prompt)
        self.assertIn("Apple", prompt)
        self.assertIn("AAPL", prompt)
        self.assertIn("Microsoft", prompt)
    
    def test_process_llm_response(self):
        """Test processing LLM response."""
        # Test JSON-like format
        json_response = """
        {"speaker": "advisor", "text": "Hello, let's discuss Apple's performance."}
        {"speaker": "client", "text": "Sure, I'm interested in AAPL stock."}
        """
        
        lines = self.strategy.process_llm_response(json_response)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["speaker"], "1")  # advisor = 1
        self.assertEqual(lines[1]["speaker"], "0")  # client = 0
        self.assertIn("Apple", lines[0]["text"])
        self.assertIn("AAPL", lines[1]["text"])
        
        # Test fallback with no matches
        bad_response = "This is not a valid conversation format"
        lines = self.strategy.process_llm_response(bad_response)
        self.assertEqual(len(lines), 2)  # Should create default lines
        self.assertEqual(lines[0]["speaker"], "1")  # First message should be advisor
        self.assertEqual(lines[1]["speaker"], "0")  # Second message should be client


if __name__ == '__main__':
    unittest.main()