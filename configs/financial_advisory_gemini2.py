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

# Datetime Distribution Configuration
DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "business_hours"  # Options: business_hours, uniform, custom_period

# Time period for conversations (ISO format)
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-03-31T23:59:59"  # Q1 2024

# Business hours settings
BUSINESS_HOURS_START = 9  # 9 AM
BUSINESS_HOURS_END = 17   # 5 PM
WEEKEND_WEIGHT = 0.0      # 20% of conversations on weekends

# Day of week weights (must sum to 1.0 for weekdays)
WEEKDAY_WEIGHTS = {
    'Monday': 0.25,
    'Tuesday': 0.2,
    'Wednesday': 0.2,
    'Thursday': 0.2,
    'Friday': 0.15
}

# Hour distribution weights
HOUR_WEIGHTS = {
    'morning': 0.3,     # 9am-12pm
    'afternoon': 0.5,   # 12pm-5pm
    'evening': 0.2      # 5pm-8pm
}

# Message timing settings
MESSAGE_DELAY_MEAN = 60     # Mean delay between messages in seconds
MESSAGE_DELAY_STD_DEV = 30  # Standard deviation for delay

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"