# # Google Cloud Configuration
# PROJECT_ID = "sk-ml-inference"
# LOCATION = "us-central1"  
# MODEL_NAME = "gemini-1.5-flash-002"  

# PERSONAS = [
#     "Sell-side Analyst",
#     "Buy-side Analyst",
#     "Portfolio Manager",    
#     "Research Analyst"
# ]

# CONVERSATION_TYPES = [
#     "Trade discussions",
#     "Deal negotiations",
#     "Stock analysis",
#     "Market updates",
#     "News on specific companies",
#     "Earnings reports discussions"
# ]

# MESSAGE_FORMATS = {
#     "Trade discussions": "informal",
#     "Deal negotiations": "informal",
#     "Stock analysis": "formal",
#     "Market updates": "formal",
#     "News on specific companies": "formal",
#     "Earnings reports discussions": "formal"
# }


# # Input Configuration
# TAXONOMY_FILE = "taxonomy.json"
# ADVISOR_NAMES = [
#     "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
#     "Eve Davis", "Frank Miller", "Grace Wilson", "Hank Moore",
#     "Ivy Taylor", "Jack Anderson"
# ]
# CLIENT_NAMES = [
#     "Allen", "Betty", "Charles", "Diana", "Edward",
#     "Fiona", "George", "Hannah", "Ian", "Julia"
# ]

# # Output Configuration
# OUTPUT_DIR = "synthetic_data"
# JSON_VERSION = "2"

# # Chat Generation Configuration
# NUM_CONVERSATIONS = 10  # Total number of conversations to generate
# MIN_MESSAGES = 2
# MAX_MESSAGES = 15

# # Topic Distribution Configuration
# TOPIC_DISTRIBUTION = "uniform"  # or specify a custom distribution

# # Logging Configuration
# LOG_FILE = "synthetic_chat_generator.log"

### CONFIG V2
import os

# Google Cloud Configuration
PROJECT_ID = "sk-ml-inference"
LOCATION = "us-central1"
MODEL_NAME = "gemini-1.5-flash-002"

TEMPERATURE = 0.3 # .2
TOP_P = 1
TOP_K = 40 #32

# Input Configuration
TAXONOMY_FILE = "taxonomy.json" # Use taxonomy.json from root for financial advisor conversations or from taxonomies dir for company tagging
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
# Updated Financial Advisory Configuration
PERSONAS = [
    "Senior Wealth Advisor",
    "Investment Portfolio Manager",
    "Retirement Planning Specialist",
    "Private Banking Client",
    "High-Net-Worth Investor"
]

CONVERSATION_TYPES = [
    # Core taxonomy categories
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

# Path to the company data CSV file (NEEDED IF COMPANY_TARGETING is enabled)
COMPANY_DATA_FILE = ""

# Company targeting configuration
COMPANY_TARGETING = {
    "enabled": False,  # Set to False to disable company-specific targeting
    "probability": 0.8,  # Probability of including companies when enabled (0.0-1.0)
    "min_companies": 1,  # Minimum number of companies to include when targeting is enabled (only used if taxonomy doesn't define company_count_options)
    "max_companies": 3   # Maximum number of companies to include when targeting is enabled (only used if taxonomy doesn't define company_count_options)
}

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
NUM_CONVERSATIONS = 20  # Reduced to 100 for initial target as per requirements
MIN_MESSAGES = 2
MAX_MESSAGES = 10

# Topic Distribution Configuration
TOPIC_DISTRIBUTION = "uniform"  # or specify a custom distribution

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"