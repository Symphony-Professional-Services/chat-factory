#!/usr/bin/env python3

"""
process_synthetic_data.py

This script processes synthetic chat data by:
1. Creating a copy of the original synthetic data to ensure data integrity.
2. Extracting and retaining only the 'version' and 'lines' fields from each conversation.
3. Splitting multiple conversations within a single JSON file into separate files.
4. Renaming each processed file to follow the '{client_name}_{conversation_number}.json' format.
5. Storing the processed files in a new directory while maintaining the original advisor-client structure.

Usage:
    python process_synthetic_data.py [--source SOURCE_DIR] [--target TARGET_DIR]

Example:
    python process_synthetic_data.py --source "synthetic_data/" --target "processed_synthetic_data/"
"""

import os
import json
import shutil
from pathlib import Path
import argparse
import logging

def setup_logging():
    """
    Sets up the logging configuration.
    """
    logging.basicConfig(
        filename='process_synthetic_data.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Process synthetic chat data.")
    parser.add_argument('--source', type=str, default='synthetic_data/', help='Path to the source synthetic data directory.')
    parser.add_argument('--target', type=str, default='processed_synthetic_data/', help='Path to the target processed data directory.')
    return parser.parse_args()

def copy_data(source_dir, target_dir):
    """
    Copies the synthetic data from source_dir to target_dir.

    Parameters:
    - source_dir (Path): Path to the source synthetic data directory.
    - target_dir (Path): Path to the target processed data directory.
    """
    try:
        if target_dir.exists():
            logging.info(f"Target directory '{target_dir}' already exists. Removing it for a fresh copy.")
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        logging.info(f"Copied data from '{source_dir}' to '{target_dir}'.")
    except Exception as e:
        logging.error(f"Failed to copy data from '{source_dir}' to '{target_dir}': {e}")
        raise

def process_conversations(target_dir):
    """
    Processes each JSON file in the target_dir by splitting conversations into separate files.

    Parameters:
    - target_dir (Path): Path to the target processed data directory.
    """
    for advisor_dir in target_dir.iterdir():
        if advisor_dir.is_dir():
            advisor_name = advisor_dir.name
            logging.info(f"Processing advisor: {advisor_name}")
            for client_file in advisor_dir.glob('*.json'):
                client_name = client_file.stem  
                try:
                    with open(client_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    conversations = data.get('conversations', [])
                    version = data.get('version', '1')
                    
                    if not conversations:
                        logging.warning(f"No conversations found in '{client_file}'. Skipping.")
                        continue
                    
                    for idx, conv in enumerate(conversations, start=1):
                        processed_conv = {
                            "version": version,
                            "lines": conv.get('lines', [])
                        }
                        
                        # Define the new filename
                        new_filename = f"{client_name}_{idx}.json"
                        new_file_path = advisor_dir / new_filename
                        
                        # Write the processed conversation to the new file
                        with open(new_file_path, 'w', encoding='utf-8') as nf:
                            json.dump(processed_conv, nf, indent=4)
                        
                        logging.info(f"Created '{new_file_path}'.")
                    
                    # remove the original client file after processing
                    os.remove(client_file)
                    logging.info(f"Removed original file '{client_file}'.")
                
                except json.JSONDecodeError:
                    logging.error(f"JSON decoding failed for file '{client_file}'. Skipping.")
                except Exception as e:
                    logging.error(f"Failed to process file '{client_file}': {e}")

def main():
    setup_logging()
    
    args = parse_arguments()
    source_dir = Path(args.source)
    target_dir = Path(args.target)
    
    if not source_dir.exists() or not source_dir.is_dir():
        logging.error(f"Source directory '{source_dir}' does not exist or is not a directory.")
        return
    
    copy_data(source_dir, target_dir)  
    process_conversations(target_dir)
    
    logging.info("Data processing completed successfully.")

if __name__ == "__main__":
    main()
