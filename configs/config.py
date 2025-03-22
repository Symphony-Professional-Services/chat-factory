### CONFIG V2
import os

# Google Cloud Configuration
PROJECT_ID = "sym-professional-services"
LOCATION = "us-central1"
MODEL_NAME = "gemini-1.5-flash-002"

TEMPERATURE = 0.3 # .2
TOP_P = 1
TOP_K = 40 #32

# Input Configuration
TAXONOMY_FILE = "taxonomy.json" # We might not need this anymore, but let's keep it for now.
ADVISOR_NAMES = [
    "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
    "Eve Davis", "Frank Miller", "Grace Wilson", "Hank Moore",
    "Ivy Taylor", "Jack Anderson"
]
CLIENT_NAMES = [
    "Allen", "Betty", "Charles", "Diana", "Edward",
    "Fiona", "George", "Hannah", "Ian", "Julia"
]

# -------- NEW CONFIGURATION FOR COMPANY TAGGING DATASET --------
PERSONAS = [
    "Sell-side Analyst",
    "Buy-side Analyst",
    "Portfolio Manager",
    "Research Analyst"
]

CONVERSATION_TYPES = [
    "Trade discussions",
    "Deal negotiations",
    "Stock analysis",
    "Market updates",
    "News on specific companies",
    "Earnings reports discussions"
]

MESSAGE_FORMATS = {
    "Trade discussions": "informal",
    "Deal negotiations": "informal",
    "Stock analysis": "formal",
    "Market updates": "formal",
    "News on specific companies": "formal",
    "Earnings reports discussions": "formal"
}

# Path to the company data CSV file
COMPANY_DATA_FILE = "company_data.csv"


MESSAGE_LENGTH_RATIO = { # Approximate ratio of message lengths (can be adjusted)
    "short": 0.4,  # 30% short messages
    "medium": 0.3, # 50% medium messages
    "long": 0.3   # 20% long messages
}

FEW_SHOT_EXAMPLES_DIR = "few_shot_examples" # Directory to store few-shot example files

CONVERSATION_MANIFEST_DIR = "conversation_scripts"  # Add this line

# -------- END NEW CONFIGURATION --------

# Output Configuration
OUTPUT_DIR = "synthetic_data"
JSON_VERSION = "5"

# Chat Generation Configuration
NUM_CONVERSATIONS = 100  # Reduced to 100 for initial target as per requirements
MIN_MESSAGES = 2
MAX_MESSAGES = 10

# Topic Distribution Configuration
TOPIC_DISTRIBUTION = "uniform"  # or specify a custom distribution

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"