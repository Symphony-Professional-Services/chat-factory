#!/bin/bash

# File: run_and_log.sh

# Description:
# This script runs the synthetic chat data generation script (main.py) and then the analytics script (metrics.py).
# It logs all outputs and errors to a log file for tracking.

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
echo "Running main.py..." | tee -a "$LOG_FILE"

# Create the synthetic_data directory if it doesn't exist and set permissions
mkdir -p synthetic_data
chmod -R 777 synthetic_data

# Run main.py and log output and errors
#poetry run python main.py >> "$LOG_FILE" 2>&1
poetry run python main.py --run_id "$RUN_ID" >> "$LOG_FILE" 2>&1


# Check if main.py ran successfully
if [ $? -ne 0 ]; then
    echo "main.py encountered an error. Check the log file for details." | tee -a "$LOG_FILE"
    exit 1
fi

echo "main.py completed successfully." | tee -a "$LOG_FILE"

# Log the start of analytics
echo "Running metrics.py..." | tee -a "$LOG_FILE"

# Run metrics.py with run_id and metadata, log output and errors
poetry run python metrics.py --run_id "$RUN_ID" --metadata "$METADATA" >> "$LOG_FILE" 2>&1

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
