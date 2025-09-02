"""
Configuration for company tagging use case with Gemini 2.0 models.

This configuration extends the base company_tagging.py config but uses the
more advanced Gemini 2.0 models via the GenAI SDK for improved entity recognition.
"""

import os
from pathlib import Path

# Import base configuration
from .company_tagging import *

# Override LLM Settings for Gemini 2.0
MODEL_NAME = "gemini-2.0-flash-001"  # Using Gemini 2.0 flash model
API_VERSION = "v1"  # API version for GenAI SDK
USE_GENAI_SDK = True  # Explicitly use the GenAI SDK

# Adjust settings for Gemini 2.0
TEMPERATURE = 0.4  # Slightly higher temperature for more creative variations
TOP_P = 0.95

# Use enhanced taxonomy with additional conversation types
TAXONOMY_FILE = "taxonomies/company_tagging_gemini2.json"

# Use expanded company data file with more companies and variations
COMPANY_DATA_FILE = "company_data_gemini2.csv"
# TODO : CLEAN UP THIS CHUNK (REDUNDANT)
# Update conversation types to include new types in the enhanced taxonomy
CONVERSATION_TYPES = [
    "Trade discussions",
    "Deal negotiations",
    "Stock analysis",
    "Market updates",
    "News on specific companies",
    "Earnings reports discussions",
    "Cross-industry comparisons",
    "Technology disruption analysis"
]

# Increase conversation generation count
NUM_CONVERSATIONS = 100  # Generate more conversations with Gemini 2.0

# Run ID prefix for tracking
RUN_ID_PREFIX = "gemini2_companies"

# Slightly increase message limits for more thorough discussions
MIN_MESSAGES = 5
MAX_MESSAGES = 15

# Enhanced company targeting settings
COMPANY_TARGETING = {
    "enabled": True,
    "probability": 1.0,
    "min_companies": 2,
    "max_companies": 5  # Increased max companies per conversation
}

# Include company_tagging.txt examples
FEW_SHOT_EXAMPLES_FILES = {
    "Trade discussions": ["Trade discussions.txt", "company_tagging.txt"],
    "Stock analysis": ["Stock analysis.txt", "company_tagging.txt"],
    "Earnings reports discussions": ["Earnings reports discussions.txt", "company_tagging.txt"],
    "Market updates": ["Market updates.txt", "company_tagging.txt"],
    "News on specific companies": ["News on specific companies.txt", "company_tagging.txt"],
    "Deal negotiations": ["Deal negotiations.txt", "company_tagging.txt"],
    "Cross-industry comparisons": ["company_tagging.txt"],
    "Technology disruption analysis": ["company_tagging.txt"]
}

# Logging
LOG_FILE = "company_tagging_gemini2_generator.log"