# Synthetic Chat Data Generation and Analytics

## Overview

This project facilitates the generation of synthetic chat conversations between financial advisors and high net worth clients. It also provides tools to analyze the generated data, offering insights into conversation patterns, topics, and more. The setup includes configuration files, taxonomy definitions, data generation scripts, analytics tools, and automation scripts to streamline the workflow.

## Directory Structure

synthetic_chat_project/ ├── synthetic_data/ │ ├── Advisor1/ │ │ └── Client1.json │ ├── Advisor2/ │ │ └── Client2.json │ └── ... ├── taxonomy.json ├── config.py ├── main.py ├── metrics.py ├── display_metrics.py ├── run_and_log.sh ├── synthetic_chat_generator.log ├── metrics_log.csv ├── run_and_log.log └── README.md


## Components

### 1. `main.py` - Synthetic Data Generation Script

Generates synthetic chat conversations based on predefined advisors, clients, categories, and topics.

- **Functionality**:
  - Selects random advisors and clients.
  - Assigns random attributes (e.g., age, communication style).
  - Constructs prompts for the language model to generate realistic conversations.
  - Saves the generated conversations in structured JSON files under `synthetic_data/`.

- **Usage**:

FOR DATA GENERATION AND RUN LOGGING: sh run.sh

FOR METRICS: python display_metrics.py
FOR SPECIFIC RUN
- python metrics.py --run_id <your_run_id> --metadata "Optional metadata for this run"
Replace <your_run_id> with the actual run ID (e.g., timestamp directory name).
FOR GLOBAL
- python metrics.py --repo_metrics
FOR OBO SCRIPT FORMAT: python process_synthetic_data.py

## Additional Notes

Data Storage:
Generated conversations are stored in synthetic_data/AdvisorName/ClientName.json.
Logging:
Regularly monitor log files (synthetic_chat_generator.log, run_and_log.log) for any errors or important information.
Metrics Tracking:
metrics_log.csv maintains a history of all analytics runs, facilitating trend analysis over time.
Customization:
Extend taxonomy.json and config.py to include more advisors, clients, categories, and topics as needed.
Error Handling:
The scripts include basic error handling. For more robust solutions, consider enhancing exception management and validation.



### Docker Build
sudo docker build -t synthetic-chat-generator . --no-cache

docker run -it --rm -v $(pwd)/synthetic_data:/app/synthetic_data synthetic-chat-generator 
docker run -it --rm -v $(pwd):/app synthetic-chat-generator 

docker run -it --rm \
    -v $(pwd):/app \
    -v $(pwd)/google-service-account.json:/app/service-account-key.json \
    -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json \
    synthetic-chat-generator


### BASH SCRIPT INSIDE OF DOCKER IMAGE (USE FOR DEBUG: OPENS A BASH TERMINAL INSIDE OF CONTAINER)
docker run -it --entrypoint bash synthetic-chat-generator



NEED TO FIX LINES LIKE THIS WITH \u2013 text:
                    "text": "Morning Betty.  Saw the preliminary Q3 earnings report for Amer Sports (AMS.HE) \u2013 slightly below expectations, impacting their share price.  Any thoughts on how this might affect their partnership with  Adidas (ADS.DE)?  Also,  I'm keeping a close eye on Citigroup (C) and their exposure to the current turmoil in the commercial real estate market.  Meanwhile,  Morgan Stanly's (MS) recent report on Copasa (CPAS3.SA) is quite bullish, a stark contrast to the generally bearish sentiment surrounding Brazilian utilities.  Have you had a chance to review it?"


NEED TO IMPROVE VARIABILITY / JUDGE/FILTER USING EMBEDDINGS TO FIND DIVERSITY OF CONTENT

NEED TO IMPROVE TAXONOMY IMPORT AND REDO INTEGRATION WITH CONFIG FILE 
NEED TO MAKE IT MORE FLEXIBLE AND MODULAR - GET DAG DESIGN OF CODE

### Post - Processing : company tagging
- post_processing_add_company_entities.py




##### TODO:

1. Resolve issue where output data is only using parent topic (and not using the subtopics - this is for the messaging analytics use case (not company tagging))
2. Resolve issue with topics being selected using distribution (make sure that's how it is done)
3. Increase time length of data so it can be greater than 3 months
4. Add in extremes (very high and low message count/topic count) [identify client/fa pairs for extrems in config and also topics to set as extremes]
5. Random selection noisy topic/conversation (super sub topic or something random)
6. Add sentiment configuration on topic and a conversation level
7. Clean up repo and make the processing much better