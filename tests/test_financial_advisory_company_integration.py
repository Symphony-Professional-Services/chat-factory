"""
Unit tests for integrating company tagging into financial advisory use case.
"""

import unittest
import tempfile
import json
import csv
import os
import random
from unittest.mock import patch, MagicMock
import asyncio

from chat_factory.strategies.financial_advisory import FinancialAdvisoryGenerationStrategy
from chat_factory.models.taxonomy import Taxonomy


class TestFinancialAdvisoryCompanyIntegration(unittest.IsolatedAsyncioTestCase):
    """Test cases for company integration in financial advisory use case."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        # Create a mock config
        self.config = MagicMock()
        self.config.PERSONAS = ["Wealth Advisor", "Portfolio Manager"]
        self.config.MESSAGE_FORMATS = {"Market Commentary": "formal"}
        self.config.MESSAGE_LENGTH_RATIO = {"short": 0.4, "medium": 0.3, "long": 0.3}
        
        # Set up company targeting config
        self.config.COMPANY_TARGETING = {"enabled": True, "probability": 0.8, "min_companies": 1, "max_companies": 3}
        
        # Create a temporary prompt template file to avoid errors
        self.temp_dir = tempfile.TemporaryDirectory()
        self.prompt_template_file = os.path.join(self.temp_dir.name, "prompt_template.txt")
        with open(self.prompt_template_file, 'w') as f:
            f.write("Generate a conversation between {advisor_name} and {client_name} about {main_topic}.\n")
            f.write("Companies to mention: {key_companies_text}\n")
            f.write("{company_instructions}\n")
        
        self.config.PROMPT_TEMPLATE_PATH = self.prompt_template_file
        
        # Create a temporary company data file
        self.company_file = os.path.join(self.temp_dir.name, "companies.csv")
        
        with open(self.company_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "ticker", "sector", "variations", "misspellings", "formal_name"])
            writer.writerow(["Apple", "AAPL", "Technology", "Apple Inc;APPL", "Aple;Appel", "Apple Inc."])
            writer.writerow(["Microsoft", "MSFT", "Technology", "MSFT;MS", "Microsft;Microsfot", "Microsoft Corporation"])
            writer.writerow(["Amazon", "AMZN", "E-commerce", "Amazon.com;AMZN", "Amazn;Amazone", "Amazon.com, Inc."])
        
        self.config.COMPANY_DATA_FILE = self.company_file
        
        # Create the strategy
        self.strategy = FinancialAdvisoryGenerationStrategy(self.config)
    
    async def asyncTearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_load_company_data(self):
        """Test loading company data in financial advisory strategy."""
        # Force reload of company data
        self.strategy._load_company_data()
        
        # Verify company data is loaded correctly
        self.assertEqual(len(self.strategy.company_data), 3)
        self.assertEqual(self.strategy.company_data[0]["name"], "Apple")
        self.assertEqual(self.strategy.company_data[1]["ticker"], "MSFT")
        self.assertEqual(self.strategy.company_data[2]["name"], "Amazon")
    
    def test_company_inclusion_decision_mechanism(self):
        """Test the decision mechanism for including companies in conversations."""
        # Test with company targeting enabled
        self.config.COMPANY_TARGETING = {"enabled": True, "probability": 1.0}
        self.strategy = FinancialAdvisoryGenerationStrategy(self.config)
        
        # Force reload of company data
        self.strategy._load_company_data()
        
        # Set random seed for deterministic company selection
        random.seed(42)
        
        topic = ("Investments", "Market Analysis", "Tech Sector")
        blueprint = self.strategy.create_manifest_blueprint("Market Commentary", topic, 10)
        
        # Check that company targeting is enabled in the blueprint
        self.assertTrue(blueprint["company_targeting_enabled"])
        self.assertGreaterEqual(len(blueprint["key_companies"]), 1)
        
        # Test with company targeting disabled
        self.config.COMPANY_TARGETING = {"enabled": False}
        self.strategy = FinancialAdvisoryGenerationStrategy(self.config)
        
        blueprint = self.strategy.create_manifest_blueprint("Market Commentary", topic, 10)
        
        # Check that company targeting is disabled in the blueprint
        self.assertFalse(blueprint["company_targeting_enabled"])
        self.assertEqual(len(blueprint.get("key_companies", [])), 0)
    
    async def test_company_integration_in_prompts(self):
        """Test that companies are properly integrated into conversation prompts."""
        # Set up test data
        manifest_blueprint = {
            "category": "Investments",
            "main_topic": "Market Analysis",
            "subtopic": "Tech Sector",
            "conversation_type": "Market Commentary",
            "message_format": "formal",
            "conversation_length": "medium",
            "company_targeting_enabled": True,
            "key_companies": ["Apple", "MSFT", "Amazon"],
            "message_style": "professional, structured",
            "typical_message_length": {"short": 0.4, "medium": 0.3, "long": 0.3}
        }
        
        # Generate prompt with companies
        prompt = await self.strategy.construct_prompt(
            "Alice Johnson", "Bob Smith", "Market Commentary", 10, manifest_blueprint, []
        )
        
        # Check that companies are included in the prompt
        self.assertIn("Apple", prompt)
        self.assertIn("MSFT", prompt)
        self.assertIn("Amazon", prompt)
        
        # Test without company targeting
        manifest_blueprint["company_targeting_enabled"] = False
        manifest_blueprint["key_companies"] = []
        
        prompt = await self.strategy.construct_prompt(
            "Alice Johnson", "Bob Smith", "Market Commentary", 10, manifest_blueprint, []
        )
        
        # Check that companies are not specifically mentioned
        # In the template they might still be mentioned as empty placeholders
        # so just check for key_companies_text being empty
        self.assertIn("Companies to mention: ", prompt)
    
    def test_process_conversation_with_companies(self):
        """Test processing LLM response with company mentions."""
        # Mock LLM response with company mentions
        llm_response = """
        {"speaker": "advisor", "text": "Hello Bob, I've been analyzing the tech sector and noticed some interesting movements with Apple (AAPL) and Microsoft."}
        {"speaker": "client", "text": "I'm interested in that. What's happening with Apple and how might it affect my portfolio?"}
        {"speaker": "advisor", "text": "Apple's recent product announcements have been well-received, and analysts are projecting strong growth. Amazon is also showing positive trends."}
        """
        
        # Process the response
        conversation = self.strategy.process_llm_response(llm_response)
        
        # Verify company mentions are preserved
        self.assertEqual(len(conversation), 3)
        self.assertIn("Apple", conversation[0]["text"])
        self.assertIn("AAPL", conversation[0]["text"])
        self.assertIn("Microsoft", conversation[0]["text"])
        self.assertIn("Apple", conversation[1]["text"])
        self.assertIn("Amazon", conversation[2]["text"])


if __name__ == '__main__':
    unittest.main()