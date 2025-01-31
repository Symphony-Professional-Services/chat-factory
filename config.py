# config.py

import os

# Google Cloud Configuration
PROJECT_ID = "PROJECT ID"
LOCATION = "LOCATION"  
MODEL_NAME = "gemini-1.5-flash-002"  

# Input Configuration
TAXONOMY_FILE = "taxonomy.json"
ADVISOR_NAMES = [
    "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
    "Eve Davis", "Frank Miller", "Grace Wilson", "Hank Moore",
    "Ivy Taylor", "Jack Anderson"
]
CLIENT_NAMES = [
    "Allen", "Betty", "Charles", "Diana", "Edward",
    "Fiona", "George", "Hannah", "Ian", "Julia"
]

# Output Configuration
OUTPUT_DIR = "synthetic_data"
JSON_VERSION = "2"

# Chat Generation Configuration
NUM_CONVERSATIONS = 500  # Total number of conversations to generate
MIN_MESSAGES = 2
MAX_MESSAGES = 15

# Topic Distribution Configuration
TOPIC_DISTRIBUTION = "uniform"  # or specify a custom distribution

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"
