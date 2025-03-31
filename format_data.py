#!/usr/bin/env python3
"""
format_data.py

Processes validated synthetic chat data into the final desired format:
1. Reads multi-conversation JSON files from the generator output directory.
2. Extracts only the 'version' and 'lines' fields for each individual conversation.
3. Creates a target directory structure: target_dir/advisor_name/
4. Saves each individual conversation into a separate file named:
   target_dir/advisor_name/{client_name}_{conversation_index_in_file}.json
5. Logs the process.

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

            # Extract metadata needed for structuring output
            # Use get with defaults to handle potentially missing keys gracefully
            advisor_name = data.get('advisor', 'UnknownAdvisor')
            client_name = data.get('client', 'UnknownClient') # Base client name for the file
            version = data.get('version', '1.0') # Use a default version
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
                    logging.warning(f"Skipping non-dictionary item in 'conversations' list within {file_path}.")
                    continue

                # Extract only required fields
                processed_conv = {
                    "version": version,
                    # Use get with default empty list for lines
                    "lines": conv.get('lines', [])
                }

                # Define the new filename using the sane client name and index
                new_filename = f"{sane_client_name}_{idx}.json"
                new_file_path = advisor_target_dir / new_filename

                # Write the processed conversation to the new file
                try:
                    with open(new_file_path, 'w', encoding='utf-8') as nf:
                        json.dump(processed_conv, nf, indent=2) # Use indent=2 for readability
                    # logging.info(f"Created '{new_file_path}'") # Can be very verbose
                    output_conversation_count += 1
                except IOError as e:
                     logging.error(f"Failed to write output file {new_file_path}: {e}")
                except Exception as e:
                     logging.error(f"Unexpected error writing file {new_file_path}: {e}", exc_info=True)

            processed_file_count += 1
            # Optionally remove the original source file *after* successful processing
            # try:
            #     os.remove(file_path)
            #     logging.debug(f"Removed original file '{file_path}'.")
            # except OSError as e:
            #     logging.warning(f"Could not remove original file {file_path}: {e}")

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
         logging.error("Source and target directories cannot be the same.")
         return

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"ERROR: Source directory '{source_dir}' does not exist or is not a directory.")
        logging.error(f"Source directory '{source_dir}' does not exist or is not a directory.")
        return

    # Setup logging - use a log file within the target directory?
    run_id = source_dir.name # Assume source dir name is the run_id
    log_file = target_dir.parent / f"format_data_{run_id}.log" # Place log outside target data
    setup_logging(log_file)

    logging.info(f"Starting data formatting process.")
    logging.info(f"Source directory: {source_dir}")
    logging.info(f"Target directory: {target_dir}")

    process_and_format_data(source_dir, target_dir)

    logging.info("Data formatting completed.")
    print("\nData formatting completed.")

if __name__ == "__main__":
    main()