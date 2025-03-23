"""
Configuration for company tagging use case.
"""

import os
from pathlib import Path

# Project Configuration
PROJECT_ID = "sym-professional-services"
LOCATION = "us-central1"
RUN_ID = None  # Will be generated automatically if not provided

# LLM Settings
LLM_PROVIDER = "vertex_ai"
MODEL_NAME = "gemini-1.5-flash-002"
TEMPERATURE = 0.3
TOP_P = 1.0
TOP_K = 40

# Strategy Configuration
TAXONOMY_STRATEGY = "company_tagging"
GENERATION_STRATEGY = "company_tagging" 
FEW_SHOT_STRATEGY = "basic"

# File Paths
TAXONOMY_FILE = "taxonomies/company_tagging.json"
FEW_SHOT_EXAMPLES_DIR = "few_shot_examples"
CONVERSATION_MANIFEST_DIR = "conversation_scripts"
COMPANY_DATA_FILE = "company_data.csv"

# Output Configuration
OUTPUT_DIR = "synthetic_data"
JSON_VERSION = "5"

# Conversation Generation Settings
# Set to a smaller number for testing, increase for production use
NUM_CONVERSATIONS = 50
MIN_MESSAGES = 4  # Increased minimum for company tagging use case
MAX_MESSAGES = 12  # Increased maximum for company tagging use case

# Personas and Participants
PERSONAS = [
    "Sell-side Analyst",
    "Buy-side Analyst",
    "Portfolio Manager",
    "Research Analyst",
    "Investment Advisor",
    "Equity Analyst",
    "Market Strategist"
]

ADVISOR_NAMES = [
    "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
    "Eve Davis", "Frank Miller", "Grace Wilson", "Hank Moore",
    "Ivy Taylor", "Jack Anderson"
]

CLIENT_NAMES = [
    "Allen", "Betty", "Charles", "Diana", "Edward",
    "Fiona", "George", "Hannah", "Ian", "Julia"
]

# Conversation Types
CONVERSATION_TYPES = [
    "Trade discussions",
    "Deal negotiations",
    "Stock analysis",
    "Market updates",
    "News on specific companies",
    "Earnings reports discussions"
]

# Message Formatting
MESSAGE_FORMATS = {
    "Trade discussions": "informal",
    "Deal negotiations": "formal",
    "Stock analysis": "formal",
    "Market updates": "formal",
    "News on specific companies": "formal",
    "Earnings reports discussions": "formal"
}

MESSAGE_LENGTH_RATIO = {
    "short": 0.3,
    "medium": 0.4,
    "long": 0.3
}

# Company Targeting is always enabled for this use case
COMPANY_TARGETING = {
    "enabled": True,
    "probability": 1.0,
    "min_companies": 2,
    "max_companies": 4
}

# Distribution Settings
TOPIC_DISTRIBUTION = "uniform"

# Logging
LOG_FILE = "company_tagging_generator.log"