# #!/bin/bash

# # File: run_and_log.sh

# # Description:
# # This script runs the synthetic chat data generation script (main.py)
# # and then the analytics script (metrics.py). It logs all outputs and errors 
# # to a log file, and ensures that output logs (including skipped files) are 
# # written to a directory that is mapped to the host.

# # Set the log file path
# LOG_FILE="run_and_log.log"

# # Generate a unique run ID using the current date and time
# RUN_ID="run_$(date +"%Y_%m_%d_%H%M%S")"

# # Capture the start time
# START_TIME=$(date +"%Y-%m-%dT%H:%M:%SZ")

# # Define metadata
# METADATA="Run initiated at ${START_TIME}"

# # Log the start of the run
# echo "============================================" | tee -a "$LOG_FILE"
# echo "Run ID: ${RUN_ID}" | tee -a "$LOG_FILE"
# echo "Start Time: ${START_TIME}" | tee -a "$LOG_FILE"
# echo "Metadata: ${METADATA}" | tee -a "$LOG_FILE"
# echo "Running main.py..." | tee -a "$LOG_FILE"

# # Create the synthetic_data directory if it doesn't exist and set permissions
# mkdir -p synthetic_data
# chmod -R 777 synthetic_data

# # Create output directory for logs (ensure /app/output is mapped to host)
# mkdir -p output/logs
# chmod -R 777 output

# # Run main.py with the run ID and log output and errors
# poetry run python main.py --run_id "$RUN_ID" >> "$LOG_FILE" 2>&1

# # Check if main.py ran successfully
# if [ $? -ne 0 ]; then
#     echo "main.py encountered an error. Check the log file for details." | tee -a "$LOG_FILE"
#     exit 1
# fi

# echo "main.py completed successfully." | tee -a "$LOG_FILE"

# # Log the start of metrics
# echo "Running metrics.py..." | tee -a "$LOG_FILE"

# # Run metrics.py with run ID and metadata, log output and errors
# poetry run python metrics.py --run_id "$RUN_ID" --metadata "$METADATA" >> "$LOG_FILE" 2>&1

# # Check if metrics.py ran successfully
# if [ $? -ne 0 ]; then
#     echo "metrics.py encountered an error. Check the log file for details." | tee -a "$LOG_FILE"
#     exit 1
# fi

# echo "metrics.py completed successfully." | tee -a "$LOG_FILE"

# # Capture the end time
# END_TIME=$(date +"%Y-%m-%dT%H:%M:%SZ")

# # Log the end of the run
# echo "End Time: ${END_TIME}" | tee -a "$LOG_FILE"
# echo "Run completed successfully." | tee -a "$LOG_FILE"
# echo "============================================" | tee -a "$LOG_FILE"
# echo "" | tee -a "$LOG_FILE"

# # Exit successfully
# exit 0


#!/bin/bash

# File: run_and_log.sh

# Description:
# This script runs the synthetic chat data generation script (main.py),
# the analytics script (metrics.py), and optionally a post-processing script
# (post_processing_add_company_entities.py) that merges company entity information
# from manifest logs into the synthetic data output.
# All outputs and errors are logged to a log file, and output directories are created
# in a location that is mapped to the host.

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

# Create output directory for logs (ensure /app/output is mapped to host)
mkdir -p output/logs
chmod -R 777 output

# Run main.py with the run ID and log output and errors
poetry run python main.py --run_id "$RUN_ID" >> "$LOG_FILE" 2>&1

# Check if main.py ran successfully
if [ $? -ne 0 ]; then
    echo "main.py encountered an error. Check the log file for details." | tee -a "$LOG_FILE"
    exit 1
fi

echo "main.py completed successfully." | tee -a "$LOG_FILE"

# Log the start of metrics
echo "Running metrics.py..." | tee -a "$LOG_FILE"

# Run metrics.py with run ID and metadata, log output and errors
poetry run python metrics.py --run_id "$RUN_ID" --metadata "$METADATA" >> "$LOG_FILE" 2>&1

# Check if metrics.py ran successfully
if [ $? -ne 0 ]; then
    echo "metrics.py encountered an error. Check the log file for details." | tee -a "$LOG_FILE"
    exit 1
fi

echo "metrics.py completed successfully." | tee -a "$LOG_FILE"

# OPTIONAL POST-PROCESSING STEP:
# Uncomment the following line if you wish to run the post-processing script to merge company entity data
# into the synthetic data output.
#
# This script (post_processing_add_company_entities.py) will:
#   - Take the run_id and process the conversation manifest logs from the conversation_manifest directory.
#   - Merge the key_companies (as structured entities) into the corresponding synthetic data files.
#   - Write the merged files to processed_synthetic_data/<run_id>/ preserving directory structure.
#
# Ensure that the directory for output (e.g., /app/processed_synthetic_data) is volume-mounted so that you can access the merged files.
#
# echo "Post Processing Step: Adding company metadata to output..."
# poetry run python post_processing_add_company_entities.py --run_id "$RUN_ID"
# echo "Post Processing Complete!"

# Capture the end time
END_TIME=$(date +"%Y-%m-%dT%H:%M:%SZ")

# Log the end of the run
echo "End Time: ${END_TIME}" | tee -a "$LOG_FILE"
echo "Run completed successfully." | tee -a "$LOG_FILE"
echo "============================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Exit successfully
exit 0
