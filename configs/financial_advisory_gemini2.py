"""
Configuration for financial advisory use case using Gemini 2.0.
"""

# Google Cloud Configuration
PROJECT_ID = "sk-ml-inference"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.0-flash-001"  # Using Gemini 2.0 model
API_VERSION = "v1"  # API version for GenAI SDK
USE_GENAI_SDK = True  # Explicitly use the GenAI SDK

# Provider Selection
PROVIDER = "vertex_ai"  # Still using the same provider name

# Strategy Selection
TAXONOMY_STRATEGY = "financial_advisory"
GENERATION_STRATEGY = "financial_advisory"
FEW_SHOT_STRATEGY = "basic"

# LLM Settings
TEMPERATURE = 0.3  # Slightly higher temperature for Gemini 2.0
TOP_P = 0.95
TOP_K = 40
MAX_OUTPUT_TOKENS = 1024

PRESENCE_PENALTY = 0.0
FREQUENCY_PENALTY = 0.0
#STOP_SEQUENCES = ["\n"]


# Input Configuration
TAXONOMY_FILE = "taxonomies/financial_advisory.json"
ADVISOR_NAMES = [
    "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
    "Eve Davis", "Frank Miller", "Grace Wilson", "Hank Moore",
    "Ivy Taylor", "Jack Anderson"
]
CLIENT_NAMES = [
    "Allen", "Betty", "Charles", "Diana", "Edward",
    "Fiona", "George", "Hannah", "Ian", "Julia"
]

# Personas and Conversation Types
PERSONAS = [
    "Senior Wealth Advisor",
    "Investment Portfolio Manager",
    "Retirement Planning Specialist",
    "Private Banking Client",
    "High-Net-Worth Investor"
]

CONVERSATION_TYPES = [
    "Small Talk",
    "Market Commentary",
    "Client Personal Concerns",
    "Product & Service Inquiry",
    "Business/Advisory",
]

MESSAGE_FORMATS = {
    "Small Talk": "informal",
    "Market Commentary": "structured",
    "Client Personal Concerns": "confidential",
    "Product & Service Inquiry": "formal",
    "Business/Advisory": "formal",
    "Financial Goals & Planning": "formal"
}

# Few-Shot Examples Configuration
FEW_SHOT_EXAMPLES_DIR = "few_shot_examples"

# Company Targeting Configuration (Optional for Financial Advisory)
COMPANY_DATA_FILE = ""
COMPANY_TARGETING = {
    "enabled": False,
    "probability": 0.8,
    "min_companies": 1,
    "max_companies": 3
}

# Message Length Configuration
MESSAGE_LENGTH_RATIO = {
    "short": 0.4,
    "medium": 0.3,
    "long": 0.3
}

# Output and Manifest Configuration
CONVERSATION_MANIFEST_DIR = "conversation_scripts"
OUTPUT_DIR = "synthetic_data"
JSON_VERSION = "5"

# Generation Volume Configuration
NUM_CONVERSATIONS = 20
MIN_MESSAGES = 2
MAX_MESSAGES = 10

# Distribution Configuration
TOPIC_DISTRIBUTION = "uniform"

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"