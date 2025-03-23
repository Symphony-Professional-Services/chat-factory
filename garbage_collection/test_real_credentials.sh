#!/bin/bash

# File: test_real_credentials.sh
#
# Description:
# This script tests the Chat Factory with real Google Cloud credentials.
# It first runs a test with the mock provider to verify basic functionality,
# then attempts to run with real Google Cloud credentials if available.

# Set the log file path
LOG_FILE="test_credentials.log"

# Generate a unique run ID using the current date and time
RUN_ID="test_$(date +"%Y_%m_%d_%H%M%S")"

# Capture the start time
START_TIME=$(date +"%Y-%m-%dT%H:%M:%SZ")

# Clear previous log and start fresh
> "$LOG_FILE"

# Log the start of the run
echo "============================================" | tee -a "$LOG_FILE"
echo "Credential Testing Run" | tee -a "$LOG_FILE"
echo "Run ID: ${RUN_ID}" | tee -a "$LOG_FILE"
echo "Start Time: ${START_TIME}" | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"

# Create required directories
mkdir -p synthetic_data output/logs few_shot_examples conversation_scripts
chmod -R 777 synthetic_data output few_shot_examples conversation_scripts

# -------------------------------------------------
# STEP 1: Test with mock provider (no credentials needed)
# -------------------------------------------------
echo -e "\nStep 1: Testing with mock provider..." | tee -a "$LOG_FILE"

# Run the financial advisory generator with mock provider
poetry run python run_financial_advisory_mock.py --run_id "${RUN_ID}_mock" --num 2 >> "$LOG_FILE" 2>&1

# Check if the generator ran successfully
if [ $? -eq 0 ]; then
    echo "✅ Mock provider test successful!" | tee -a "$LOG_FILE"
    echo "Generated files in synthetic_data/${RUN_ID}_mock/" | tee -a "$LOG_FILE"
else
    echo "❌ Mock provider test failed. See log for details." | tee -a "$LOG_FILE"
    exit 1
fi

# -------------------------------------------------
# STEP 2: Check if credentials file exists
# -------------------------------------------------
echo -e "\nStep 2: Checking for Google Cloud credentials..." | tee -a "$LOG_FILE"

# Try different possible credential file names
CREDENTIAL_FILES=("google-service-account.json" "service-account-key.json" "credentials.json")
CRED_FILE=""

for file in "${CREDENTIAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        CRED_FILE="$file"
        echo "Found credential file: $CRED_FILE" | tee -a "$LOG_FILE"
        break
    fi
done

if [ -z "$CRED_FILE" ]; then
    echo "❌ No credential file found. Skipping Vertex AI test." | tee -a "$LOG_FILE"
    echo "To test with real credentials, place a Google Cloud service account key file" | tee -a "$LOG_FILE"
    echo "in the project directory with one of these names:" | tee -a "$LOG_FILE"
    echo "  - google-service-account.json" | tee -a "$LOG_FILE"
    echo "  - service-account-key.json" | tee -a "$LOG_FILE"
    echo "  - credentials.json" | tee -a "$LOG_FILE"
    exit 0
fi

# -------------------------------------------------
# STEP 3: Create a temporary config file that uses Vertex AI
# -------------------------------------------------
echo -e "\nStep 3: Creating test config with Vertex AI provider..." | tee -a "$LOG_FILE"

# Create a temporary config file based on financial_advisory.py with Vertex AI provider
cp configs/financial_advisory.py configs/test_vertex_ai.py

# Add LLM_PROVIDER = 'vertex_ai' to the config
# Make a backup first
cp configs/test_vertex_ai.py configs/test_vertex_ai.py.bak

# Make sure this only affects the temporary test file
if grep -q "LLM_PROVIDER" configs/test_vertex_ai.py; then
    # If LLM_PROVIDER is already defined, update it
    sed -i 's/LLM_PROVIDER = .*/LLM_PROVIDER = "vertex_ai"/' configs/test_vertex_ai.py
else
    # Otherwise, add it after the LLM Settings line
    sed -i 's/# LLM Settings/# LLM Settings\nLLM_PROVIDER = "vertex_ai"/' configs/test_vertex_ai.py
fi

# Reduce the number of conversations for this test
sed -i 's/NUM_CONVERSATIONS = [0-9]*/NUM_CONVERSATIONS = 2/' configs/test_vertex_ai.py

# Set environment variable for credentials
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/$CRED_FILE"

# -------------------------------------------------
# STEP 4: Test with Vertex AI provider
# -------------------------------------------------
echo -e "\nStep 4: Testing with Vertex AI provider..." | tee -a "$LOG_FILE"
echo "Using credential file: $CRED_FILE" | tee -a "$LOG_FILE"
echo "GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS" | tee -a "$LOG_FILE"

# Create a custom run script for this test
cat > run_test_vertex_ai.py << EOF
#!/usr/bin/env python3
"""
Test script for Vertex AI with real credentials.
"""

import asyncio
import argparse
import sys
import logging
import os


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Vertex AI Credentials Test')
    parser.add_argument("--run_id", type=str, default="${RUN_ID}_vertex", help="Run ID for this test")
    parser.add_argument("--num", type=int, default=2, help="Number of conversations to generate")
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set up detailed logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Log credential path to verify it's accessible
    credential_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')
    logging.info(f"Using credentials from: {credential_path}")
    if not os.path.exists(credential_path):
        logging.error(f"Credential file does not exist: {credential_path}")
        sys.exit(1)
    
    try:
        # Import from the new framework
        from chat_factory.config import load_config_from_file
        from chat_factory.llm import create_llm_provider
        from chat_factory.strategies import (
            create_taxonomy_strategy,
            create_generation_strategy,
            create_few_shot_strategy
        )
        from chat_factory.generator import SyntheticChatGenerator
        
        # Load the test Vertex AI config
        config = load_config_from_file("configs/test_vertex_ai.py")
        
        # Update config with command line arguments
        if args.run_id:
            config.RUN_ID = args.run_id
        
        if args.num:
            config.NUM_CONVERSATIONS = args.num
        
        # Log configuration details
        logging.info(f"Using Project ID: {config.PROJECT_ID}")
        logging.info(f"Using Location: {config.LOCATION}")
        logging.info(f"Using Model: {config.MODEL_NAME}")
        logging.info(f"Using Provider: {getattr(config, 'LLM_PROVIDER', 'vertex_ai')}")
        
        # Create the strategies
        taxonomy_strategy = create_taxonomy_strategy(config.TAXONOMY_STRATEGY, config)
        generation_strategy = create_generation_strategy(config.GENERATION_STRATEGY, config)
        few_shot_strategy = create_few_shot_strategy(config.FEW_SHOT_STRATEGY, config)
        llm_provider = create_llm_provider(getattr(config, 'LLM_PROVIDER', 'vertex_ai'), config)
        
        # Initialize the LLM provider to test credentials
        logging.info(f"Initializing LLM provider...")
        await llm_provider.initialize()
        logging.info(f"Successfully initialized LLM provider!")
        
        # Create the generator
        generator = SyntheticChatGenerator(
            config=config,
            taxonomy_strategy=taxonomy_strategy,
            generation_strategy=generation_strategy,
            few_shot_strategy=few_shot_strategy,
            llm_provider=llm_provider
        )
        
        # Run the generator
        logging.info(f"Starting generation with Vertex AI...")
        await generator.generate_synthetic_data()
        logging.info(f"Completed conversation generation!")
        
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x run_test_vertex_ai.py

# Run the test
poetry run python run_test_vertex_ai.py >> "$LOG_FILE" 2>&1

# Check if the generator ran successfully
if [ $? -eq 0 ]; then
    echo "✅ Vertex AI provider test successful!" | tee -a "$LOG_FILE"
    echo "Generated files in synthetic_data/${RUN_ID}_vertex/" | tee -a "$LOG_FILE"
else
    echo "❌ Vertex AI provider test failed. See log for details." | tee -a "$LOG_FILE"
    
    # Print last 20 lines of log for quick diagnosis
    echo -e "\nLast 20 lines of log:" | tee -a "$LOG_FILE"
    tail -n 20 "$LOG_FILE" | tee -a /dev/stdout
fi

# -------------------------------------------------
# STEP 5: Clean up
# -------------------------------------------------
echo -e "\nStep 5: Cleaning up temporary files..." | tee -a "$LOG_FILE"

# Remove temporary files
rm -f configs/test_vertex_ai.py
rm -f configs/test_vertex_ai.py.bak
rm -f run_test_vertex_ai.py

echo -e "\nTest complete! See $LOG_FILE for detailed logs." | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"