"""
Mock LLM provider for testing.
"""

import logging
import random
from typing import Optional

from .base import LLMProvider


class MockLLMProvider(LLMProvider):
    """
    A mock LLM provider that returns predefined responses for testing.
    """
    
    def __init__(self, config):
        """
        Initialize the mock LLM provider.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
    
    async def initialize(self):
        """
        Initialize the mock LLM provider.
        """
        logging.info("Initializing Mock LLM Provider")
    
    async def generate_content(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Generate mock content based on the prompt.
        
        Args:
            prompt: The prompt to generate content for
            max_tokens: Maximum number of tokens to generate (ignored in mock)
            
        Returns:
            Mock conversation text
        """
        # Return a different mock conversation based on what's in the prompt
        logging.info(f"Generating mock content for prompt (first 100 chars): {prompt[:100]}...")
        
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
        elif "Product & Service Inquiry" in prompt:
            return """
            {"speaker": "advisor", "text": "What kinds of investment products are you interested in learning more about?"}
            {"speaker": "client", "text": "I'm curious about alternatives to traditional stocks and bonds."}
            {"speaker": "advisor", "text": "We offer several alternative investment options, including private equity, hedge funds, and real estate investment trusts."}
            {"speaker": "client", "text": "Could you tell me more about the REITs? I've been thinking about real estate exposure."}
            """
        elif "Business/Advisory" in prompt:
            return """
            {"speaker": "advisor", "text": "Let's review your investment portfolio performance over the past quarter."}
            {"speaker": "client", "text": "That would be great. I noticed some of my tech stocks have been down."}
            {"speaker": "advisor", "text": "Yes, the tech sector has faced some headwinds recently, but your diversified approach has helped mitigate those losses."}
            {"speaker": "client", "text": "That's good to hear. What adjustments would you recommend at this point?"}
            """
        elif "Client Personal Concerns" in prompt:
            return """
            {"speaker": "advisor", "text": "How's your family doing? Last time we spoke, your daughter was starting college."}
            {"speaker": "client", "text": "Thanks for asking. She's doing well, but the tuition bills have been a bit of a shock."}
            {"speaker": "advisor", "text": "I understand. Would you like to review your education funding strategy?"}
            {"speaker": "client", "text": "Yes, I think we should look at whether I need to adjust my monthly contributions."}
            """
        elif "company_targeting_enabled" in prompt or "prominently feature" in prompt:
            # Extract company names from the prompt
            import re
            company_names = []
            if "following companies" in prompt:
                companies_section = prompt.split("following companies:", 1)[1].split("\n", 1)[0]
                company_names = [c.strip() for c in companies_section.split(",")]
            
            # If we couldn't extract companies, use some defaults
            if not company_names:
                company_names = ["Apple", "Microsoft", "Google"]
            
            # Ensure we have at least 2 companies for the template
            if len(company_names) < 2:
                if "Apple" not in company_names:
                    company_names.append("Apple")
                elif "Microsoft" not in company_names:
                    company_names.append("Microsoft")
                else:
                    company_names.append("Google")
            
            # Get first company and its ticker (or use a default)
            company1 = company_names[0]
            try:
                if len(company1.split()) > 0:
                    ticker1 = company1.split()[0][:4].upper() if len(company1.split()[0]) >= 4 else company1.split()[0].upper()
                else:
                    ticker1 = "TICK"
            except:
                ticker1 = "TICK"
            
            # Get second company
            company2 = company_names[1]
            
            # Create a simple mock conversation with company mentions
            return f"""
            {{"speaker": "advisor", "text": "Let's discuss the recent earnings report from {company1}. They've shown impressive growth this quarter."}}
            {{"speaker": "client", "text": "I've been following {company1} closely. What specific numbers stood out to you?"}}
            {{"speaker": "advisor", "text": "{company1} reported revenue growth of 15% year-over-year, exceeding analyst expectations by a significant margin."}}
            {{"speaker": "client", "text": "That's impressive. How does that compare to {company2}? I know they're in a similar space."}}
            {{"speaker": "advisor", "text": "While {company2} also had a strong quarter, they only saw about 8% growth. {company1} is clearly outperforming in the current market."}}
            {{"speaker": "client", "text": "What about their stock performance? Is now a good time to invest in either company?"}}
            {{"speaker": "advisor", "text": "{company1} stock ({ticker1}) is trading at a higher P/E ratio than {company2}, but I believe they have more room for growth in the long term."}}
            {{"speaker": "client", "text": "Thanks for the insights. I think I'll increase my position in {company1} based on this analysis."}}
            """
        else:
            return """
            {"speaker": "advisor", "text": "Hello, how can I help you today?"}
            {"speaker": "client", "text": "I'd like to discuss my investment strategy."}
            {"speaker": "advisor", "text": "Of course. What specific aspects are you interested in reviewing?"}
            {"speaker": "client", "text": "I'm wondering if I should rebalance my portfolio given recent market conditions."}
            """
    
    async def retry_with_backoff(self, prompt: str, max_retries: int = 10, 
                          initial_backoff: float = 1.0, max_backoff: float = 32.0) -> str:
        """
        Mock implementation of retry_with_backoff that simply calls generate_content.
        
        Args:
            prompt: The prompt to generate content for
            max_retries: Maximum number of retry attempts (ignored in mock)
            initial_backoff: Initial backoff time in seconds (ignored in mock)
            max_backoff: Maximum backoff time in seconds (ignored in mock)
            
        Returns:
            Mock conversation text
        """
        return await self.generate_content(prompt)