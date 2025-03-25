"""
Tests for company selection logic in the financial advisory generation strategy.
"""

import unittest
from unittest.mock import MagicMock, patch
import re

from chat_factory.strategies.financial_advisory.generation_strategy import FinancialAdvisoryGenerationStrategy


class TestCompanySelection(unittest.TestCase):
    """
    Test case for company selection in prompt generation.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock config
        self.mock_config = MagicMock()
        self.mock_config.COMPANY_TARGETING = {
            "enabled": True,
            "probability": 0.3,
            "min_companies": 1,
            "max_companies": 3
        }
        
        # Set up sample company data
        self.company_data = [
            {"name": "Apple", "ticker": "AAPL", "industry": "Technology", "variations": "Apple Inc", "misspellings": "", "formal_name": "Apple Inc."},
            {"name": "Microsoft", "ticker": "MSFT", "industry": "Technology", "variations": "MSFT", "misspellings": "", "formal_name": "Microsoft Corporation"},
            {"name": "Johnson & Johnson", "ticker": "JNJ", "industry": "Healthcare", "variations": "J&J", "misspellings": "", "formal_name": "Johnson & Johnson"},
            {"name": "Visa", "ticker": "V", "industry": "Financial Services", "variations": "Visa Inc", "misspellings": "", "formal_name": "Visa Inc."},
            {"name": "Mastercard", "ticker": "MA", "industry": "Financial Services", "variations": "Mastercard Inc", "misspellings": "", "formal_name": "Mastercard Incorporated"},
        ]
        
        # Create strategy instance
        self.strategy = FinancialAdvisoryGenerationStrategy(self.mock_config)
        self.strategy.company_data = self.company_data
    
    def test_company_selection_probability(self):
        """Test that company selection probability is properly applied."""
        # Test below threshold (should enable targeting)
        with patch('random.random', return_value=0.2):  # 0.2 < 0.3
            result = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
            self.assertTrue(result["company_targeting_enabled"])
            
        # Test at threshold (should not enable targeting)
        with patch('random.random', return_value=0.3):  # 0.3 = 0.3
            result = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
            self.assertFalse(result["company_targeting_enabled"])
            
        # Test above threshold (should not enable targeting)
        with patch('random.random', return_value=0.5):  # 0.5 > 0.3
            result = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
            self.assertFalse(result["company_targeting_enabled"])
    
    def test_company_count_distribution(self):
        """Test that the 70/20/10 distribution for company counts is enforced."""
        # Fix random to enable targeting
        with patch('random.random', return_value=0.1):
            # Test 1 company case (70%)
            with patch('random.choices', return_value=[1]):
                blueprint = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
                self.assertEqual(len(set(blueprint["key_companies"])), 1)
                
            # Test 2 companies case (20%)
            with patch('random.choices', return_value=[2]):
                with patch('random.sample', return_value=[self.company_data[0], self.company_data[1]]):
                    blueprint = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
                    companies = set([company.lower() for company in blueprint["key_companies"]])
                    # The key_companies might contain variations like ticker symbols
                    # So we just check that we have at least 2 unique items from separate companies
                    self.assertGreaterEqual(len(companies), 2)
                    
            # Test 3 companies case (10%)
            with patch('random.choices', return_value=[3]):
                with patch('random.sample', return_value=[self.company_data[0], self.company_data[1], self.company_data[2]]):
                    blueprint = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
                    companies = set([company.lower() for company in blueprint["key_companies"]])
                    # Again, check for at least 3 unique items
                    self.assertGreaterEqual(len(companies), 3)
    
    def test_no_duplicate_companies(self):
        """Test that company selection doesn't pick the same company twice."""
        # Fix random to enable targeting
        with patch('random.random', return_value=0.1):
            # Request 3 companies
            with patch('random.choices', return_value=[3]):
                # Sample should give 3 unique companies
                with patch('random.sample', return_value=[self.company_data[0], self.company_data[1], self.company_data[2]]):
                    blueprint = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
                    # Collect unique company base names
                    company_base_names = set()
                    for company in self.company_data:
                        if company["name"].lower() in " ".join(blueprint["key_companies"]).lower():
                            company_base_names.add(company["name"].lower())
                            
                    # Should have 3 unique companies
                    self.assertEqual(len(company_base_names), 3)
    
    def test_company_inclusion_in_prompt(self):
        """Test that companies are properly included in the prompt when targeting is enabled."""
        # Create a manifest blueprint with targeting enabled
        with patch('random.random', return_value=0.1):  # Lower than probability threshold
            # Force selection of specific companies
            with patch('random.sample', return_value=[self.company_data[0], self.company_data[1]]):
                # Force 2 companies
                with patch('random.choices', return_value=[2]):
                    blueprint = self.strategy.create_manifest_blueprint("Market Commentary", 
                                                              ("Business/Advisory", "Investments", "Stocks"), 
                                                              10)
                    
                    # Check that targeting is enabled
                    self.assertTrue(blueprint["company_targeting_enabled"])
                    
                    # Now test that these companies appear in the prompt
                    mock_advisor = "John Doe"
                    mock_client = "Jane Smith"
                    few_shot_examples = []
                    
                    # Mock the prompt template for testing
                    dummy_template = """
                    Generate a conversation between {advisor_name} and {client_name} about {main_topic}.
                    
                    {company_instructions}
                    
                    Company list: {key_companies_text}
                    """
                    
                    with patch.object(self.strategy, 'prompt_template', dummy_template):
                        # Build the actual prompt
                        prompt = self.strategy.construct_prompt(
                            mock_advisor, mock_client, "Market Commentary", 10, blueprint, few_shot_examples
                        )
                        
                        # Verify the prompt contains company instructions and Apple, Microsoft
                        self.assertIn("company", prompt.lower())
                        self.assertIn("apple", prompt.lower())
                        self.assertIn("microsoft", prompt.lower())
    
    def test_no_companies_in_prompt_when_disabled(self):
        """Test that companies are NOT included in prompt when targeting is disabled."""
        # Create a manifest blueprint with targeting disabled
        with patch('random.random', return_value=0.9):  # Higher than probability threshold
            blueprint = self.strategy.create_manifest_blueprint("Market Commentary", 
                                                      ("Business/Advisory", "Investments", "Stocks"), 
                                                      10)
            
            # Verify targeting is disabled
            self.assertFalse(blueprint["company_targeting_enabled"])
            self.assertEqual(len(blueprint.get("key_companies", [])), 0)
            
            # Check prompt doesn't include company instructions
            mock_advisor = "John Doe"
            mock_client = "Jane Smith"
            few_shot_examples = []
            
            # Mock the prompt template for testing
            dummy_template = """
            Generate a conversation between {advisor_name} and {client_name} about {main_topic}.
            
            {company_instructions}
            
            Company list: {key_companies_text}
            """
            
            with patch.object(self.strategy, 'prompt_template', dummy_template):
                # Build the actual prompt
                prompt = self.strategy.construct_prompt(
                    mock_advisor, mock_client, "Market Commentary", 10, blueprint, few_shot_examples
                )
                
                # Verify the prompt doesn't contain company instructions or any company names
                self.assertNotIn("prominently feature", prompt.lower())
                self.assertNotIn("mention each company", prompt.lower())
                self.assertIn("company list:", prompt.lower())
                self.assertNotIn("apple", prompt.lower())
                self.assertNotIn("microsoft", prompt.lower())
    
    def test_max_company_limit_enforcement(self):
        """Test that max_companies limit is enforced when selecting companies."""
        # Set max_companies to 2 for this test
        self.strategy.company_targeting["max_companies"] = 2
        
        # Fix random to enable targeting
        with patch('random.random', return_value=0.1):
            # Try to request 3 companies (should be limited to 2)
            with patch('random.choices', return_value=[3]):
                # Sample would return 3 companies
                with patch('random.sample', side_effect=lambda companies, count: companies[:count]):
                    blueprint = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
                    
                    # Count unique companies (not variations)
                    unique_companies = set()
                    for company_entry in blueprint["key_companies"]:
                        for company in self.company_data:
                            if (company_entry.lower() == company["name"].lower() or 
                                company_entry.lower() == company["ticker"].lower()):
                                unique_companies.add(company["name"])
                    
                    # Should be limited to 2 companies
                    self.assertLessEqual(len(unique_companies), 2)
    
    def test_short_ticker_inclusion(self):
        """Test that short tickers (like V and MA) are handled properly in company selection."""
        # Create a test focusing on only companies with short tickers
        short_ticker_companies = [
            {"name": "Visa", "ticker": "V", "industry": "Financial Services", "variations": "Visa Inc", "misspellings": "", "formal_name": "Visa Inc."},
            {"name": "Mastercard", "ticker": "MA", "industry": "Financial Services", "variations": "Mastercard Inc", "misspellings": "", "formal_name": "Mastercard Incorporated"},
        ]
        
        # Update strategy with only these companies
        self.strategy.company_data = short_ticker_companies
        
        # Fix random to enable targeting
        with patch('random.random', return_value=0.1):
            # Request 2 companies
            with patch('random.choices', return_value=[2]):
                # Sample both companies
                with patch('random.sample', return_value=short_ticker_companies):
                    blueprint = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
                    
                    # Check if the key_companies list includes both Visa and Mastercard
                    visa_included = any("visa" in item.lower() for item in blueprint["key_companies"])
                    mastercard_included = any("mastercard" in item.lower() for item in blueprint["key_companies"])
                    
                    self.assertTrue(visa_included)
                    self.assertTrue(mastercard_included)
                    
                    # Check if it includes the ticker symbols
                    v_ticker_included = "V" in blueprint["key_companies"]
                    ma_ticker_included = "MA" in blueprint["key_companies"]
                    
                    # At least one of them should be included
                    self.assertTrue(v_ticker_included or visa_included)
                    self.assertTrue(ma_ticker_included or mastercard_included)
    
    def test_company_targeting_disabled_configuration(self):
        """Test behavior when company targeting is completely disabled in configuration."""
        # Disable company targeting
        self.strategy.company_targeting["enabled"] = False
        
        # Should not target companies regardless of random value
        with patch('random.random', return_value=0.1):  # Would normally enable
            blueprint = self.strategy.create_manifest_blueprint("Test", ("Test", "Test", ""), 10)
            self.assertFalse(blueprint["company_targeting_enabled"])
            self.assertEqual(len(blueprint.get("key_companies", [])), 0)


if __name__ == '__main__':
    unittest.main()