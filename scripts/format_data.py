#!/usr/bin/env python3
"""
format_data.py

Processes validated synthetic chat data into the final desired format:
1. Reads multi-conversation JSON files from the generator output directory.
2. Extracts 'lines' (speaker, text only) and the starting 'timestamp' for each
   individual conversation.
3. Formats the conversation timestamp to 'YYYY-MM-DD' for the metadata.
4. Creates a target directory structure: target_dir/advisor_name/
5. Saves each individual conversation into a separate file named:
   target_dir/advisor_name/{client_name}_{conversation_index_in_file}.json
   with a hardcoded version and metadata containing the formatted conversation date.
   Timestamps within the 'lines' array are removed.
6. Logs the process.

Usage:
    python format_data.py [--source SOURCE_DIR] [--target TARGET_DIR]

Example:
    python format_data.py --source "output/run_id_123/" --target "processed_data/run_id_123/"
"""

import os
import json
import shutil
from pathlib import Path
import argparse
import logging
from datetime import datetime # Added for timestamp formatting

# --- Configuration ---
# Set the desired hardcoded version for all output files
HARDCODED_VERSION = "2"
# Define the desired date format for the output metadata
DATE_FORMAT_OUTPUT = '%Y-%m-%d'

# --- Logging Setup ---
def setup_logging(log_file='format_data.log'):
    """Sets up logging configuration."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True) # Ensure log directory exists

    logging.basicConfig(
        filename=log_path,
        filemode='w', # Overwrite previous log
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

# --- Argument Parsing ---
def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Format synthetic chat data.")
    parser.add_argument('--source', required=True, help='Path to the source generator output directory (e.g., output/run_id_123).')
    parser.add_argument('--target', required=True, help='Path to the target directory for processed data.')
    return parser.parse_args()

# --- Processing Logic ---
def process_and_format_data(source_dir: Path, target_dir: Path):
    """
    Reads source files, extracts conversations, formats, and saves to target.

    Parameters:
    - source_dir (Path): Path to the source generator output directory.
    - target_dir (Path): Path to the target processed data directory.
    """
    if target_dir.exists():
        logging.warning(f"Target directory '{target_dir}' already exists. Existing files might be overwritten.")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created target directory: {target_dir}")

    processed_file_count = 0
    output_conversation_count = 0
    source_files = list(source_dir.glob('*.json')) # Get all JSON files directly

    if not source_files:
        logging.warning(f"No JSON files found in source directory: {source_dir}")
        return

    logging.info(f"Found {len(source_files)} JSON files to process in {source_dir}")

    for file_path in source_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract metadata needed for structuring output (advisor/client for paths)
            advisor_name = data.get('advisor', 'UnknownAdvisor')
            client_name = data.get('client', 'UnknownClient')
            conversations = data.get('conversations', [])

            if not isinstance(conversations, list):
                 logging.warning(f"Expected 'conversations' to be a list in {file_path}, found {type(conversations)}. Skipping file.")
                 continue

            if not conversations:
                 logging.warning(f"No conversations found in file '{file_path}'. Skipping.")
                 continue

            # Sanitize names for directory/file creation
            sane_advisor_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in advisor_name)
            sane_client_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in client_name)

            # Create advisor subdirectory in target
            advisor_target_dir = target_dir / sane_advisor_name
            advisor_target_dir.mkdir(parents=True, exist_ok=True)

            # Process each conversation within the file
            for idx, conv in enumerate(conversations, start=1):
                if not isinstance(conv, dict):
                    logging.warning(f"Skipping non-dictionary item in 'conversations' list within {file_path} at index {idx-1}.")
                    continue

                # --- MODIFIED PART 1: Extract and Format timestamp for metadata ---
                original_timestamp = conv.get('timestamp', None) # Get timestamp string
                formatted_date = "UnknownDate" # Default value

                if original_timestamp:
                    try:
                        # Attempt to parse the timestamp (handles formats like YYYY-MM-DDTHH:MM:SS)
                        dt_object = datetime.fromisoformat(original_timestamp)
                        # Format it to the desired YYYY-MM-DD format
                        formatted_date = dt_object.strftime(DATE_FORMAT_OUTPUT)
                    except ValueError:
                        # Log a warning if parsing fails
                        logging.warning(f"Could not parse timestamp '{original_timestamp}' in conversation index {idx-1} of file '{file_path}'. Using default 'UnknownDate'.")
                        # Keep formatted_date as "UnknownDate"
                    except TypeError:
                         logging.warning(f"Timestamp '{original_timestamp}' in conversation index {idx-1} of file '{file_path}' is not a string. Using default 'UnknownDate'.")
                         # Keep formatted_date as "UnknownDate"

                else:
                    logging.warning(f"Conversation index {idx-1} in file '{file_path}' is missing 'timestamp' for metadata. Using default 'UnknownDate'.")
                    # Keep formatted_date as "UnknownDate"

                # --- MODIFIED PART 2: Process lines to remove timestamps ---
                original_lines = conv.get('lines', [])
                processed_lines = [] # Initialize a new list for processed lines

                if original_lines and isinstance(original_lines, list):
                    for line_entry in original_lines:
                        if isinstance(line_entry, dict): # Ensure the line item is a dictionary
                            # Create a new dictionary containing only speaker and text
                            processed_lines.append({
                                "speaker": line_entry.get("speaker", "Unknown"), # Get speaker, default if missing
                                "text": line_entry.get("text", "") # Get text, default if missing
                            })
                        else:
                            logging.warning(f"Skipping non-dictionary item within 'lines' list in conversation index {idx-1} of file '{file_path}'. Item: {line_entry}")
                elif not original_lines:
                     logging.warning(f"Conversation index {idx-1} in file '{file_path}' has no 'lines' or 'lines' is empty. Output file will have empty lines array.")
                else:
                    logging.warning(f"Expected 'lines' to be a list in conversation index {idx-1} of file '{file_path}', but found {type(original_lines)}. Output file will have empty lines array.")

                # --- MODIFIED PART 3: Construct final output object ---
                processed_conv = {
                    "version": HARDCODED_VERSION, # Use the hardcoded version
                    "metadata": {
                        "date": formatted_date # Use the formatted date string (YYYY-MM-DD)
                    },
                    "lines": processed_lines # Use the processed lines (without timestamps)
                }
                # --- END MODIFIED PART ---

                # Define the new filename using the sane client name and index
                new_filename = f"{sane_client_name}_{idx}.json"
                new_file_path = advisor_target_dir / new_filename

                # Write the processed conversation to the new file
                try:
                    with open(new_file_path, 'w', encoding='utf-8') as nf:
                        json.dump(processed_conv, nf, indent=2) # Use indent=2 for readability
                    output_conversation_count += 1
                except IOError as e:
                     logging.error(f"Failed to write output file {new_file_path}: {e}")
                except Exception as e:
                     logging.error(f"Unexpected error writing file {new_file_path}: {e}", exc_info=True)

            processed_file_count += 1

        except json.JSONDecodeError:
            logging.error(f"JSON decoding failed for source file '{file_path}'. Skipping.")
        except Exception as e:
            logging.error(f"Failed to process source file '{file_path}': {e}", exc_info=True)

    logging.info(f"Processed {processed_file_count} source files.")
    logging.info(f"Created {output_conversation_count} individual conversation files in {target_dir}")


# --- Main Execution ---
def main():
    args = parse_arguments()
    source_dir = Path(args.source).resolve() # Use absolute path
    target_dir = Path(args.target).resolve() # Use absolute path

    # Basic validation
    if source_dir == target_dir:
         print("ERROR: Source and target directories cannot be the same.")
         return

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"ERROR: Source directory '{source_dir}' does not exist or is not a directory.")
        return

    # Setup logging
    run_id = source_dir.name
    log_file_dir = target_dir.parent if target_dir.parent != source_dir.parent else target_dir.parent / "logs"
    log_file_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_file_dir / f"format_data_{run_id}_to_{target_dir.name}.log"
    setup_logging(log_file)

    # Log errors again now that logging is configured
    if source_dir == target_dir:
        logging.error("Source and target directories cannot be the same. Exiting.")
        return
    if not source_dir.exists() or not source_dir.is_dir():
       logging.error(f"Source directory '{source_dir}' does not exist or is not a directory. Exiting.")
       return


    logging.info(f"Starting data formatting process.")
    logging.info(f"Source directory: {source_dir}")
    logging.info(f"Target directory: {target_dir}")
    logging.info(f"Output version hardcoded to: {HARDCODED_VERSION}")
    logging.info(f"Metadata date format set to: '{DATE_FORMAT_OUTPUT}'")
    logging.info("Timestamps will be removed from individual 'lines' entries.")

    process_and_format_data(source_dir, target_dir)

    logging.info("Data formatting completed.")
    print(f"\nData formatting completed. Log file: {log_file}")

if __name__ == "__main__":
    main()