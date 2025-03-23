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
    "Ivy Taylor", "Jack Anderson", "Karen Lee", "Michael Roberts",
    "Nancy Chen", "Oliver Patel", "Patricia Foster", "Quincy Thompson",
    "Rachel Garcia", "Samuel Kim", "Tina Washington", "Victor Martinez"
]
# CLIENT_NAMES = [
#     "Allen Brooks", "Betty Sanders", "Charles Wong", "Diana Martinez", "Edward Johnson",
#     "Fiona Murphy", "George Patel", "Hannah Reynolds", "Ian Cooper", "Julia Simmons",
#     "Kevin Diaz", "Layla Washington", "Marcus Chen", "Natalie Rodriguez", "Omar Scott"
# ]

CLIENT_NAMES = [
    "Allen Brooks", "Betty Sanders", "Charles Wong", "Diana Martinez", "Edward Johnson",
    "Fiona Murphy", "George Patel", "Hannah Reynolds", "Ian Cooper", "Julia Simmons",
    "Kevin Diaz", "Layla Washington", "Marcus Chen", "Natalie Rodriguez", "Omar Scott",
    "Adam Bennett", "Adriana Carter", "Alex Morgan", "Alicia Perez", "Amanda Foster",
    "Amber Ross", "Andre Thompson", "Angela Mitchell", "Anthony Russell", "Ashley Ward",
    "Austin Griffin", "Barbara James", "Benjamin Turner", "Bradley Collins", "Brenda Cook",
    "Brian Phillips", "Brittany Evans", "Bruce Bailey", "Caleb Foster", "Carla Gonzales",
    "Carolyn Parker", "Casey Torres", "Catherine Howard", "Chad Stewart", "Chloe Patterson",
    "Chris Richardson", "Christian Bell", "Christina Cox", "Christine Hayes", "Cindy Ramirez",
    "Claire Hughes", "Clayton Reed", "Colin Rivera", "Courtney Gray", "Crystal Price",
    "Curtis Jenkins", "Cynthia Peterson", "Dale Brooks", "Danielle Rogers", "Darren Coleman",
    "David Long", "Deborah Hill", "Dennis Bryant", "Derek Wood", "Dominic Powell",
    "Donna Cooper", "Dylan Ross", "Elena Morales", "Elias Simmons", "Elijah Perry",
    "Elizabeth Ward", "Emily Barnes", "Emma Kelly", "Eric Butler", "Erica Flores",
    "Erik Alexander", "Ethan Russell", "Eva Cox", "Evelyn Lee", "Felicia Adams",
    "Frank Morgan", "Gabriel Richardson", "Gabriella Ortiz", "Gary Mitchell", "Gina Sanchez",
    "Grace Stewart", "Gregory Clark", "Hailey Price", "Haley Rivera", "Harold James",
    "Heather Torres", "Henry Coleman", "Holly Patterson", "Hunter Rogers", "Isaac Powell",
    "Isabella King", "Jackie Allen", "Jacob Sanders", "Jacqueline Thomas", "James Harris",
    "Jamie Watson", "Jared Martinez", "Jasmine Gonzalez", "Jason Robinson", "Jeffrey Campbell",
    "Jennifer Davis", "Jeremiah Peterson", "Jessica Bell", "Joel Morris", "John Richardson",
    "Jordan White", "Jose Ramirez", "Joseph Cook", "Joshua Parker", "Joyce Turner",
    "Justin Murphy", "Kaitlyn Watson", "Karen Foster", "Katherine Hughes", "Kathleen Edwards",
    "Kayla Scott", "Keith Barnes", "Kelsey Hall", "Kenneth Wood", "Kimberly Green",
    "Kristen Ross", "Kyle Griffin", "Laura Powell", "Lauren Simmons", "Leah Jenkins",
    "Leonard Carter", "Leslie Alexander", "Lillian Bryant", "Lily Adams", "Linda Morris",
    "Logan Walker", "Louis Thompson", "Lucas Young", "Luis Ortiz", "Luke Morgan",
    "Madeline Brooks", "Makayla Rivera", "Malik Jackson", "Margaret Kelly", "Maria Campbell",
    "Marie Stewart", "Marissa Phillips", "Mark Reed", "Martin Peterson", "Mary Coleman",
    "Matthew Davis", "Maya Hill", "Megan Wilson", "Melanie Perez", "Melissa Baker",
    "Michael Russell", "Michelle Cooper", "Miguel Edwards", "Miranda Gray", "Monica Diaz",
    "Nancy Wood", "Naomi Watson", "Nathan Hughes", "Nicholas Foster", "Nicole Turner",
    "Nina Collins", "Noah Price", "Olivia Butler", "Oscar Ward", "Paige Roberts",
    "Pamela Cook", "Patrick Bailey", "Paul Ross", "Peter Mitchell", "Philip Richardson",
    "Priscilla Gonzales", "Rachel Bryant", "Rafael Evans", "Rebecca Simmons", "Regina Stewart",
    "Richard Powell", "Robert Johnson", "Robin Clark", "Rodney Bell", "Roger Griffin",
    "Ronald Carter", "Rosemary Lee", "Russell Brooks", "Ryan Harris", "Sabrina Parker",
    "Samuel Patterson", "Sandra Kelly", "Sarah Ramirez", "Scott James", "Sean Howard",
    "Selena Diaz", "Shane Cox", "Shannon Perry", "Shawn Butler", "Sheila Flores",
    "Shelby Alexander", "Sidney Morales", "Sierra Ross", "Simon Edwards", "Sofia Murphy",
    "Sophia Sanchez", "Spencer Richardson", "Stacy Price", "Stephanie Coleman", "Stephen Watson",
    "Steve Morgan", "Steven Rivera", "Summer Barnes", "Susan Patterson", "Sydney Martinez",
    "Tanya Torres", "Taylor Foster", "Teresa Ward", "Terry Stewart", "Theresa Jenkins",
    "Thomas Cooper", "Timothy Phillips", "Tina Scott", "Todd Gonzalez", "Tonya Brooks",
    "Tracy Rogers", "Trevor Reed", "Tristan King", "Tyler Bennett", "Valerie Hayes",
    "Vanessa Simmons", "Veronica Allen", "Victor Howard", "Victoria Perez", "Vincent Cook",
    "Virginia Martinez", "Walter Griffin", "Wayne Powell", "Whitney Reed", "William Peterson",
    "Wyatt Baker", "Xavier Collins", "Yolanda Sanders", "Zachary Carter", "Zoey Turner",
    "Aaliyah Green", "Aaron Hughes", "Abigail Campbell", "Alan Scott", "Alana Davis",
    "Albert Morris", "Alejandro Jenkins", "Alexandra Wood", "Alexis Adams", "Alice Cooper",
    "Alisha Roberts", "Allison Thompson", "Alvin White", "Amy Young", "Andre Martinez",
    "Angelina Stewart", "Annabelle Gray", "Anne Brooks", "April Richardson", "Arthur Watson",
    "Audrey Bell", "Bailey Clark", "Barry Russell", "Beatrice Cook", "Bernard Price",
    "Bethany Hall", "Bill Coleman", "Billy Collins", "Blake Reed", "Bobbie Ross",
    "Bonnie Kelly", "Brandon Powell", "Brandy Flores", "Breanna Ward", "Brent Butler",
    "Brett Ramirez", "Brianna Mitchell", "Bridget Parker", "Brock Turner", "Bryan Wood",
    "Byron Howard", "Caitlin Evans", "Candace Ortiz", "Cara Lee", "Carlos Martinez",
    "Carl Patterson", "Carmen Rogers", "Carrie Cooper", "Cassandra Young", "Cedric Rivera",
    "Celeste Hughes", "Cheryl Jenkins", "Cheyenne Carter", "Claudia Brooks", "Clifford Ward",
    "Connie Bell", "Conor Richardson", "Corey Edwards", "Cristina Perez", "Daisy Watson",
    "Dakota Morgan", "Damian Baker", "Dana Simmons", "Dante Diaz", "Darcy Foster",
    "Darius Powell", "Darlene Mitchell", "Darrell Perry", "Deanna Cook", "Dean Gonzales",
    "Delaney Ramirez", "Desiree Stewart", "Devin Bryant", "Dominique Cox", "Donovan Clark",
    "Dorothy Gray", "Douglas Patterson", "Duane Campbell", "Dustin Russell", "Dwight Collins",
    "Ebony Griffin", "Edgar Reed", "Edith Flores", "Eduardo Sanders", "Eileen Martinez",
    "Elaine Wood", "Eleanor Torres", "Elise Butler", "Emmanuel Price", "Enrique Scott",
    "Ernest Rivera", "Faith Richardson", "Fernando Barnes", "Fredrick Morgan", "Gavin Hughes"
]

# Client-Advisor Distribution Configuration
CLIENT_ADVISOR_DISTRIBUTION = {
    "enabled": True,  # Enable custom distribution of clients among advisors
    "distribution_type": "uniform",  # Changed from uniform to weighted for Pareto distribution
    # Weighted distribution - Pareto-like (20% of advisors have 80% of clients)
    "high_volume_advisor_ratio": 0.20,  # 20% of advisors are high-volume
    "high_volume_client_ratio": 0.80,  # These advisors handle 80% of clients
    # Custom distribution allows manually setting specific advisor-client pairs
    "custom_pairings": {
        # Example: "Alice Johnson": ["Allen Brooks", "Edward Johnson", "Layla Washington"]
        # Leave empty to use algorithmic distribution
    },
    # Extreme cases - can override the algorithmic distribution
    "special_cases": {
        "low_client_advisors": ["Patricia Foster", "Karen Lee"],  # Advisors with very few clients (will have 1-2 clients)
        "high_client_advisors": ["Bob Smith", "Eve Davis"]        # Advisors with many clients (will have 80-100% of clients)
    }
}

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
NUM_CONVERSATIONS = 20  # Increased to generate more diverse data
MIN_MESSAGES = 2
MAX_MESSAGES = 10

# Daily average conversations (alternative to NUM_CONVERSATIONS) 
# DAILY_CONVERSATION_TARGET = 5  # Average conversations per day
# ENFORCE_EXACT_COUNT = False    # Whether to strictly follow NUM_CONVERSATIONS

# Distribution Configuration
TOPIC_DISTRIBUTION = "uniform"

# Datetime Distribution Configuration
DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "business_hours"  # Options: business_hours, uniform, custom_period

# Time period for conversations (ISO format)
START_DATE = "2024-10-01T00:00:00"
END_DATE = "2025-03-23T23:59:59"  # Q1 2024

# Business hours settings
BUSINESS_HOURS_START = 9  # 9 AM
BUSINESS_HOURS_END = 16   # 5 PM
WEEKEND_WEIGHT = 0.05      # 20% of conversations on weekends

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
MESSAGE_DELAY_MEAN = 100     # Mean delay between messages in seconds
MESSAGE_DELAY_STD_DEV = 30  # Standard deviation for delay

# Logging Configuration
LOG_FILE = "synthetic_chat_generator.log"