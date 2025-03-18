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

# COMPANY_LIST = [
#     "Equatorial", "Omega", "Auren", "Eletrobras", "Copasa", "JPM", "Citi", "BofA",
#     "Tesla", "Apple", "Google", "Blackrock", "TotalEnergies", "Allianz", "Eni", "Meta",
#     "Amazon", "Iberdrola", "Orsted", "McKinsey", "Covivio", "Li-Auto", "Politico",
#     "Euractiv", "Adidas", "Amer Sports", "Anta Sports", "Keji", "TianYuan", "Grab",
#     "Cajamar", "Bandhan", "Remitly", "Vodacom", "Nubank", "MercadoLibre", "Ecolab",
#     "Maplecroft", "Tiktok", "Cargill", "Sons of Gwalia", "Sappi", "Kubota", "Suzano",
#     "General Motors", "Blackstone", "Tapestry"
# ]

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
# NOTE: dont want to be giving a company list and ticker list seperate....Cant see why a user would want that. Should pull ticker info from prompt/llm?
# TICKER_SYMBOLS = ["JPM", "AAPL", "TSLA", "MSFT"]
# COMMON_ABBREVIATIONS = ["JPM", "BofA", "GS", "Citi", "GOOG"] # proxy for specific terms/phrases to be used in place of a company/general
# MISSPELLINGS = ["MorganStanly", "BoA", "teslsa", "googl"] # forced mispellings that we know are common (could move this to the llm to randomly select words to mess up)
# FORMAL_NAMES = ["JPMorgan Chase", "Bank of America", "Tesla Inc.", "Alphabet Inc."] # other formal names (feels like there could be a dictionary - maybe already - that contains standard company names)


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
JSON_VERSION = "4"

# Chat Generation Configuration
NUM_CONVERSATIONS = 20  # Reduced to 100 for initial target as per requirements
MIN_MESSAGES = 2
MAX_MESSAGES = 10

# Topic Distribution Configuration
TOPIC_DISTRIBUTION = "uniform"  # or specify a custom distribution

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"