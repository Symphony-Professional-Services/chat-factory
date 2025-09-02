"""
Test script for company regex patterns.

This script tests various regex patterns used for detecting company names and tickers
in text data. It's useful for debugging issues with company mention detection.
"""

import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_ticker_regex():
    """Test various regex patterns for ticker detection."""
    
    # Sample text with various company references
    test_cases = [
        "Visa (V) is a popular credit card company",
        "I own shares of V and it's performing well",
        "The ticker V has seen significant growth",
        "V stock seems like a good investment",
        "I recommend buying V shares",
        "My position in V has grown",
        "The price of V increased by 3%",
        "Have exposure to V through an ETF",
        
        # Negative cases that shouldn't match
        "I have a very good feeling about this stock",
        "Let me give you a valid reason",
        "There's value in diversification",
        
        # Mastercard cases
        "Mastercard (MA) is another option",
        "I'm tracking MA's performance",
        "MA shares are up today",
        
        # Microsoft cases
        "Microsoft (MSFT) reported strong earnings",
        "MSFT is a technology leader",
        "$MSFT looks promising",
        
        # Apple cases
        "Apple (AAPL) has a new product",
        "I'm bullish on AAPL",
        "Apple Inc. is one of the top companies",
    ]
    
    # Test for V (Visa)
    ticker = "v"
    logging.info(f"\nTesting for ticker: {ticker.upper()}")
    
    # Patterns for very short tickers (1-2 chars)
    strict_patterns = [
        r'[$]' + re.escape(ticker) + r'\b',                     # $V
        r'\b' + re.escape(ticker) + r'[ ]?[(]',                 # V (
        r'ticker:?\s+' + re.escape(ticker) + r'\b',             # ticker: V
        r'symbol:?\s+' + re.escape(ticker) + r'\b',             # symbol: V
        r'stock:?\s+' + re.escape(ticker) + r'\b',              # stock: V  
        r'\b' + re.escape(ticker) + r'[ ]stock',                # V stock
        r'\b' + re.escape(ticker) + r'[ ]shares',               # V shares
        r'invested in ' + re.escape(ticker) + r'\b',            # invested in V
        r'buy ' + re.escape(ticker) + r'\b',                    # buy V
        r'sell ' + re.escape(ticker) + r'\b',                   # sell V
        r'trade ' + re.escape(ticker) + r'\b',                  # trade V
        r'the ' + re.escape(ticker) + r' ticker',               # the V ticker
        r'owns ' + re.escape(ticker) + r'\b',                   # owns V
        r'hold ' + re.escape(ticker) + r'\b',                   # hold V
        r'holding ' + re.escape(ticker) + r'\b',                # holding V
        r'position in ' + re.escape(ticker) + r'\b',            # position in V
        r'exposure to ' + re.escape(ticker) + r'\b',            # exposure to V
        r'returns for ' + re.escape(ticker) + r'\b',            # returns for V
        r'price of ' + re.escape(ticker) + r'\b',               # price of V
    ]
    
    for text in test_cases:
        text_lower = text.lower()
        match_found = False
        
        for pattern in strict_patterns:
            if re.search(pattern, text_lower):
                logging.info(f"MATCH found in: '{text}'")
                match_found = True
                break
        
        if not match_found:
            logging.info(f"NO MATCH in: '{text}'")
    
    # Test for MA (Mastercard)
    ticker = "ma"
    logging.info(f"\nTesting for ticker: {ticker.upper()}")
    
    for text in test_cases:
        text_lower = text.lower()
        match_found = False
        
        for pattern in strict_patterns:
            if re.search(pattern, text_lower):
                logging.info(f"MATCH found in: '{text}'")
                match_found = True
                break
        
        if not match_found:
            logging.info(f"NO MATCH in: '{text}'")
    
    # Test for MSFT (Microsoft)
    ticker = "msft"
    logging.info(f"\nTesting for ticker: {ticker.upper()}")
    
    # Patterns for typical tickers (3-4 chars)
    patterns = [
        r'[$]' + re.escape(ticker) + r'\b',                     # $MSFT
        r'\b' + re.escape(ticker) + r'\b',                      # MSFT
        r'ticker:?\s+' + re.escape(ticker) + r'\b',             # ticker: MSFT
        r'symbol:?\s+' + re.escape(ticker) + r'\b',             # symbol: MSFT
    ]
    
    for text in test_cases:
        text_lower = text.lower()
        match_found = False
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                logging.info(f"MATCH found in: '{text}'")
                match_found = True
                break
        
        if not match_found:
            logging.info(f"NO MATCH in: '{text}'")
    
    # Test for company names
    company_name = "apple"
    logging.info(f"\nTesting for company name: {company_name.title()}")
    
    pattern = r'\b' + re.escape(company_name) + r'\b'
    
    for text in test_cases:
        text_lower = text.lower()
        if re.search(pattern, text_lower):
            logging.info(f"MATCH found in: '{text}'")
        else:
            logging.info(f"NO MATCH in: '{text}'")

if __name__ == "__main__":
    test_ticker_regex()