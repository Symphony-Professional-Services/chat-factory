#!/bin/bash

# File: run.sh
#
# Description:
# This script runs the synthetic chat data generation using the new framework
# and then the analytics script (metrics.py). It logs all outputs and errors 
# to a log file and ensures that output logs are written to a mapped directory.
# Set run_*.py to run
RUN_FILE="run_financial_advisory.py"

# Set the log file path
LOG_FILE="run_and_log.log"

# Generate a unique run ID using the current date and time
RUN_ID="run_$(date +"%Y_%m_%d_%H%M%S")"

# Capture the start time
START_TIME=$(date +"%Y-%m-%dT%H:%M:%SZ")

# Define metadata
METADATA="Run initiated at ${START_TIME}"

# Log the start of the run
echo "============================================" | tee -a "$LOG_FILE"
echo "Run ID: ${RUN_ID}" | tee -a "$LOG_FILE"
echo "Start Time: ${START_TIME}" | tee -a "$LOG_FILE"
echo "Metadata: ${METADATA}" | tee -a "$LOG_FILE"
echo "Running chat factory framework..." | tee -a "$LOG_FILE"

# Create the synthetic_data directory if it doesn't exist and set permissions
mkdir -p synthetic_data
chmod -R 777 synthetic_data

# Create output directory for logs (ensure /app/output is mapped to host)
mkdir -p output/logs
chmod -R 777 output

# Create few shot examples directory if it doesn't exist
mkdir -p few_shot_examples
chmod -R 777 few_shot_examples

# Create conversation scripts directory if it doesn't exist
mkdir -p conversation_scripts
chmod -R 777 conversation_scripts

# Run the financial advisory generator with the run ID and log output and errors
echo "Running generator script: $RUN_FILE..." | tee -a "$LOG_FILE"
poetry run python "$RUN_FILE" --run_id "$RUN_ID" >> "$LOG_FILE" 2>&1

# Check if the generator ran successfully
if [ $? -ne 0 ]; then
    echo "Generator encountered an error. Check the log file for details." | tee -a "$LOG_FILE"
    exit 1
fi

echo "Generator completed successfully." | tee -a "$LOG_FILE"

# Log the start of metrics
echo "Running metrics.py..." | tee -a "$LOG_FILE"

# Run metrics.py with run ID and metadata, log output and errors
poetry run python scripts/metrics.py --run_id "$RUN_ID" --metadata "$METADATA" >> "$LOG_FILE" 2>&1

# Check if metrics.py ran successfully
if [ $? -ne 0 ]; then
    echo "metrics.py encountered an error. Check the log file for details." | tee -a "$LOG_FILE"
    exit 1
fi

echo "metrics.py completed successfully." | tee -a "$LOG_FILE"

# Capture the end time
END_TIME=$(date +"%Y-%m-%dT%H:%M:%SZ")

# Log the end of the run
echo "End Time: ${END_TIME}" | tee -a "$LOG_FILE"
echo "Run completed successfully." | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Exit successfully
exit 0