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