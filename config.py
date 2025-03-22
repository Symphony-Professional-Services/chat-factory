
# # Google Cloud Configuration
# PROJECT_ID = "PROJECT ID"
# LOCATION = "LOCATION"  
# MODEL_NAME = "gemini-1.5-flash-002"  

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
# NUM_CONVERSATIONS = 500  # Total number of conversations to generate
# MIN_MESSAGES = 2
# MAX_MESSAGES = 15

# # Topic Distribution Configuration
# TOPIC_DISTRIBUTION = "uniform"  # or specify a custom distribution

# # Logging Configuration
# LOG_FILE = "synthetic_chat_generator.log"


# Google Cloud Configuration
PROJECT_ID = "sym-professional-services"  # Replace with your actual project ID
LOCATION = "us-central1"  # Example location, adjust as needed
MODEL_NAME = "gemini-1.5-flash-002"

# Input Configuration
TAXONOMY_FILE = "taxonomy.json"
# Advisor Configuration
NUM_ADVISORS = 200
MIN_ADVISORS = 20
MAX_ADVISORS = 50  # Based on the average range
ADVISOR_NAMES_FILE = "advisor_names.txt"  # Consider using a file for a larger list
# Client Configuration
AVG_CLIENTS_PER_ADVISOR = 10
MIN_CLIENTS_PER_ADVISOR = 15
MAX_CLIENTS_PER_ADVISOR = 20
CLIENT_NAMES_FILE = "client_names.txt"  # Consider using a file for a larger list

# Time Dimension Configuration
CONVERSATION_SPAN_WEEKS = 4  # Minimum 4 weeks
WEEKEND_FREQUENCY_MULTIPLIER = 0.5  # Reduce frequency on weekends by half
WORKING_HOURS_START = 9
WORKING_HOURS_END = 17  # 5 PM (17:00 in 24-hour format)
AFTER_HOURS_FREQUENCY_REDUCTION = 0.25  # Reduce frequency to 25% after hours

# Conversation Frequency Configuration
AVG_MESSAGES_PER_DAY_PER_ADVISOR_PER_CLIENT = 45
CLIENT_INTERACTION_PROBABILITY = {
    "high": 0.8,  # Example: 80% chance of interaction weekly for high-touch
    "medium": 0.5, # Example: 50% chance of interaction monthly for medium-touch
    "low": 0.2     # Example: 20% chance of interaction quarterly for low-touch
}
PROBABILITY_CLIENT_INITIATES = 0.7  # Example: 70% chance client initiates

# Conversation Content Configuration
BASE_TOPICS = {
    "Small Talk": 0.15,  # Example base probability
    "Market Commentary": 0.20,
    "Client Personal Concerns": 0.10,
    "Product & Service Inquiry": 0.25,
    "Business/Advisory": 0.30
}
TRENDING_TOPICS = {
    "ESG Investing": {"start_date": "2025-03-01", "end_date": "2025-04-30", "probability_boost": 0.1},
    "Specific Market Event X": {"start_date": "2025-03-15", "end_date": "2025-03-22", "probability_boost": 0.15}
    # Add more trending topics with their start/end dates and probability boosts
}
TOPIC_DISTRIBUTION_TYPE = "normal"  # Consider implementing this logic
CONVERSATION_DEPTH_DISTRIBUTION = "poisson"
AVG_MESSAGES_PER_CONVERSATION = 5  # Example average for Poisson distribution
EDGE_CASE_PROBABILITY = 0.5  # 50% chance of a sub-topic conversation

# Language Style Configuration
ADVISOR_STYLE_PROFILES_FILE = "advisor_styles.json" # File to define different advisor styles

# Sentiment Configuration
SENTIMENT_PROFILES_FILE = "sentiment_profiles.json" # File to define sentiment based on client/topic

# Output Configuration
OUTPUT_DIR = "synthetic_data"
JSON_VERSION = "2"

# Chat Generation Configuration
MIN_MESSAGES_PER_CONVERSATION = 2
MAX_MESSAGES_PER_CONVERSATION = 20 # Adjust based on Conversation Depth

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"