#!/usr/bin/env python3
"""
create_validation_set.py

Reads raw synthetic chat data JSON files and creates a single CSV file
containing metadata and ground truth labels for evaluating classification models.

Output CSV Columns:
- conversation_id
- advisor
- client
- version (from source file)
- date (YYYY-MM-DD format from conversation timestamp)
- category (Ground Truth)
- topic (Ground Truth)
- company_mentions (Ground Truth, pipe-separated string)
- full_text (Concatenated conversation text for LLM input)
- source_file (Name of the source JSON file)

Usage:
    python create_validation_set.py --source SOURCE_DIR --output OUTPUT_CSV

Example:
    python create_validation_set.py --source "output/run_id_123/" --output "evaluation_data/run_id_123_validation.csv"
"""

import os
import json
import csv
from pathlib import Path
import argparse
import logging
from datetime import datetime

# --- Configuration ---
# Define the desired date format for the output CSV
DATE_FORMAT_OUTPUT = '%Y-%m-%d'
# Delimiter for joining list items (like company_mentions) in CSV
LIST_DELIMITER = '|'

# --- Logging Setup ---
def setup_logging(log_file='create_validation_set.log'):
    """Sets up basic logging configuration."""
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
    parser = argparse.ArgumentParser(description="Create validation CSV from synthetic chat data.")
    parser.add_argument('--source', required=True, help='Path to the source directory containing raw generator output JSON files.')
    parser.add_argument('--output', required=True, help='Path for the output CSV file.')
    return parser.parse_args()

# --- Processing Logic ---
def create_validation_set(source_dir: Path, output_file_path: Path):
    """
    Reads source JSONs, extracts relevant data, and writes to a CSV file.

    Parameters:
    - source_dir (Path): Path to the source generator output directory.
    - output_file_path (Path): Path to the target output CSV file.
    """
    all_conversation_data = []
    processed_file_count = 0
    source_files = list(source_dir.glob('*.json'))

    if not source_files:
        logging.warning(f"No JSON files found in source directory: {source_dir}")
        return

    logging.info(f"Found {len(source_files)} JSON files to process in {source_dir}")

    for file_path in source_files:
        logging.debug(f"Processing file: {file_path.name}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract file-level metadata
            file_version = data.get('version', 'UnknownVersion')
            advisor_name = data.get('advisor', 'UnknownAdvisor')
            client_name = data.get('client', 'UnknownClient')
            conversations = data.get('conversations', [])

            if not isinstance(conversations, list):
                 logging.warning(f"Expected 'conversations' to be a list in {file_path.name}, found {type(conversations)}. Skipping file.")
                 continue

            if not conversations:
                 logging.debug(f"No conversations found in file '{file_path.name}'.")
                 # Continue to next file, don't skip processing others
                 processed_file_count += 1
                 continue

            # Process each conversation within the file
            for idx, conv in enumerate(conversations):
                if not isinstance(conv, dict):
                    logging.warning(f"Skipping non-dictionary item in 'conversations' list within {file_path.name} at index {idx}.")
                    continue

                # Extract conversation-level data
                conv_id = conv.get('conversation_id', f"{file_path.stem}_conv_{idx}") # Generate fallback ID
                category = conv.get('category', None) # Keep None if missing
                topic = conv.get('topic', None) # Keep None if missing
                company_mentions_list = conv.get('company_mentions', [])
                original_timestamp = conv.get('timestamp', None)
                lines = conv.get('lines', [])

                # Format timestamp
                formatted_date = None # Default to None if missing or invalid
                if original_timestamp:
                    try:
                        dt_object = datetime.fromisoformat(original_timestamp)
                        formatted_date = dt_object.strftime(DATE_FORMAT_OUTPUT)
                    except (ValueError, TypeError):
                        logging.warning(f"Could not parse timestamp '{original_timestamp}' for conversation_id '{conv_id}' in file '{file_path.name}'. Date will be empty.")

                # Concatenate text lines
                full_text = ""
                if lines and isinstance(lines, list):
                    texts = [line.get('text', '') for line in lines if isinstance(line, dict) and line.get('text')]
                    full_text = "\n".join(texts).strip() # Join with newline, remove leading/trailing whitespace
                elif lines:
                     logging.warning(f"Expected 'lines' to be a list of dicts for conversation_id '{conv_id}' in file '{file_path.name}', found {type(lines)}. Full text may be incomplete.")

                # Format company mentions list
                company_mentions_str = ""
                if company_mentions_list and isinstance(company_mentions_list, list):
                    # Ensure all items are strings before joining
                    company_mentions_str = LIST_DELIMITER.join(map(str, company_mentions_list))
                elif company_mentions_list:
                    logging.warning(f"Expected 'company_mentions' to be a list for conversation_id '{conv_id}' in file '{file_path.name}', found {type(company_mentions_list)}. Field will be empty.")


                # Append data for this conversation
                all_conversation_data.append({
                    'conversation_id': conv_id,
                    'advisor': advisor_name,
                    'client': client_name,
                    'version': file_version,
                    'date': formatted_date if formatted_date else '', # Use empty string for CSV if None
                    'category': category if category else '', # Use empty string for CSV if None
                    'topic': topic if topic else '', # Use empty string for CSV if None
                    'company_mentions': company_mentions_str,
                    'full_text': full_text,
                    'source_file': file_path.name
                })

            processed_file_count += 1

        except json.JSONDecodeError:
            logging.error(f"JSON decoding failed for source file '{file_path.name}'. Skipping.")
        except IOError as e:
             logging.error(f"Failed to read source file '{file_path.name}': {e}")
        except Exception as e:
            logging.error(f"Unexpected error processing file '{file_path.name}': {e}", exc_info=True)

    logging.info(f"Processed {processed_file_count} source files.")

    # Write data to CSV
    if not all_conversation_data:
        logging.warning("No conversation data extracted. Output CSV file will be empty or not created.")
        # Optional: Create empty file with header anyway?
        # header = [...]
        # with open(...) as f: csv.DictWriter(f, fieldnames=header).writeheader()
        return

    # Define CSV header order - explicitly list columns
    header = [
        'conversation_id', 'advisor', 'client', 'version', 'date',
        'category', 'topic', 'company_mentions', 'full_text', 'source_file'
    ]

    logging.info(f"Writing {len(all_conversation_data)} conversation records to {output_file_path}...")
    try:
        # Ensure target directory exists
        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header, quoting=csv.QUOTE_MINIMAL) # Use minimal quoting
            writer.writeheader()
            writer.writerows(all_conversation_data)
        logging.info("Successfully wrote validation dataset CSV.")

    except IOError as e:
        logging.error(f"Failed to write output CSV file {output_file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error writing CSV file {output_file_path}: {e}", exc_info=True)


# --- Main Execution ---
def main():
    args = parse_arguments()
    source_dir = Path(args.source).resolve()
    output_file = Path(args.output).resolve()

    # Basic validation
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"ERROR: Source directory '{source_dir}' does not exist or is not a directory.")
        return
    if output_file.is_dir():
         print(f"ERROR: Output path '{output_file}' is a directory, please specify a file path.")
         return
    if source_dir == output_file.parent:
        print(f"Warning: Output file '{output_file.name}' will be created inside the source directory '{source_dir}'.")


    # Setup logging - log file relative to output file?
    log_file = output_file.parent / f"{output_file.stem}.log"
    setup_logging(log_file)

    # Log errors again now that logging is configured
    if not source_dir.exists() or not source_dir.is_dir():
       logging.error(f"Source directory '{source_dir}' does not exist or is not a directory. Exiting.")
       return
    if output_file.is_dir():
         logging.error(f"Output path '{output_file}' is a directory. Exiting.")
         return


    logging.info("Starting validation dataset creation process.")
    logging.info(f"Source directory: {source_dir}")
    logging.info(f"Output CSV file: {output_file}")

    create_validation_set(source_dir, output_file)

    logging.info("Validation dataset creation process completed.")
    print(f"\nValidation dataset creation completed. Log file: {log_file}")

if __name__ == "__main__":
    main()