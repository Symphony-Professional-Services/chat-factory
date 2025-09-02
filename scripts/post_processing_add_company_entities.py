#!/usr/bin/env python3
import os
import json
import argparse
import logging
import shutil
from pathlib import Path
import glob
import re
import inspect

# Configure logging to include filename and line number
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Merge manifest company entities into synthetic data output based on conversation_id."
    )
    parser.add_argument("--run_id", type=str, required=True, help="Run ID to process.")
    parser.add_argument("--manifest_dir", type=str, default="conversation_scripts", help="Directory where manifest logs are stored.")
    parser.add_argument("--synthetic_dir", type=str, default="synthetic_data", help="Base directory for synthetic data output.")
    parser.add_argument("--output_dir", type=str, default="processed_synthetic_data", help="Directory to write merged output.")
    return parser.parse_args()


def load_manifest_mapping(run_id: str, manifest_dir: Path) -> dict:
    """
    Scans manifest log files in manifest_dir that match the run_id.
    Extracts JSON blocks from the logs that are delimited by
    ---BEGIN_MANIFEST--- and ---END_MANIFEST---.
    
    This function strips out the logging prefixes from each line so that
    the actual JSON can be reconstructed, and then builds a mapping from
    conversation_id (from generated_conversation) to key_companies (from blueprint).
    """
    manifest_mapping = {}
    pattern = f"*{run_id}*.log"
    manifest_files = list(manifest_dir.glob(pattern))
    logging.info(f"Found {len(manifest_files)} manifest file(s) matching pattern {pattern} in {manifest_dir}")
    
    for mf in manifest_files:
        try:
            with mf.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            
            in_block = False
            block_lines = []
            for line in lines:
                # Remove logging prefix: assume the log message is after the second " - "
                # For example, "2025-03-18 18:21:31,673 - INFO - ---BEGIN_MANIFEST---"
                parts = line.split(" - ", 2)
                message = parts[2].strip() if len(parts) == 3 else line.strip()
                
                if message == "---BEGIN_MANIFEST---":
                    in_block = True
                    block_lines = []  # Reset block accumulator
                    continue
                elif message == "---END_MANIFEST---":
                    in_block = False
                    json_str = "\n".join(block_lines)
                    try:
                        manifest_obj = json.loads(json_str)
                        gen_conv = manifest_obj.get("generated_conversation", {})
                        conv_id = gen_conv.get("conversation_id")
                        blueprint = manifest_obj.get("blueprint", {})
                        key_companies = blueprint.get("key_companies")
                        if conv_id and key_companies:
                            manifest_mapping[conv_id] = key_companies
                            logging.debug(f"Loaded manifest for conversation {conv_id}")
                        else:
                            logging.warning(f"Missing conv_id or key_companies in manifest block from file {mf}")
                    except json.JSONDecodeError as e:
                        logging.error(f"Error decoding JSON block in file {mf}: {e}", exc_info=True)
                    block_lines = []  # Clear after processing
                    continue

                if in_block:
                    block_lines.append(message)
        except Exception as e:
            logging.error(f"Error reading manifest file {mf}: {e}", exc_info=True)
    
    logging.info(f"Loaded manifest mapping for {len(manifest_mapping)} conversations.")
    return manifest_mapping


def merge_manifest_into_synthetic(run_id: str, synthetic_dir: Path, output_dir: Path, manifest_mapping: dict):
    """
    Iterates over synthetic JSON files in synthetic_dir/<run_id>/.
    For each conversation in each file, if the conversation_id exists in manifest_mapping,
    update the conversation by adding a "key_companies" field.
    Write updated files to output_dir/<run_id>/ preserving directory structure.
    """
    run_input_dir = synthetic_dir / run_id
    run_output_dir = output_dir / run_id
    run_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Assume synthetic data files are stored under synthetic_dir/<run_id>/<advisor>/<client>.json
    json_files = list(run_input_dir.glob("*/*.json"))
    logging.info(f"Found {len(json_files)} synthetic JSON files under {run_input_dir}")
    
    files_merged = 0
    for file_path in json_files:
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Validate structure: expect a dict with a key "conversations" that is a list.
            if not (isinstance(data, dict) and "conversations" in data and isinstance(data["conversations"], list)):
                logging.warning(f"Skipping file {file_path}: Unexpected structure")
                continue
            
            updated = False
            # Iterate over each conversation in the file.
            for conv in data["conversations"]:
                conv_id = conv.get("conversation_id")
                if conv_id and conv_id in manifest_mapping:
                    # Update conversation with key_companies from manifest mapping.
                    conv["key_companies"] = manifest_mapping[conv_id]
                    updated = True
                    logging.debug(f"Merged manifest data for conversation {conv_id} in file {file_path}")
            
            if updated:
                # Preserve directory structure: synthetic_dir/<run_id>/<advisor>/<client>.json
                advisor_dir = file_path.parent.name
                out_dir = run_output_dir / advisor_dir
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / file_path.name
                with out_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                files_merged += 1
                logging.info(f"Merged manifest data into file {out_file}")
            else:
                logging.debug(f"No manifest data found for file {file_path}")
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}", exc_info=True)
    
    logging.info(f"Merged manifest data into {files_merged} files out of {len(json_files)} synthetic files.")

def main():
    args = parse_arguments()
    run_id = args.run_id
    manifest_dir = Path(args.manifest_dir)
    synthetic_dir = Path(args.synthetic_dir)
    output_dir = Path(args.output_dir)
    
    logging.info(f"Post-processing run_id: {run_id}")
    logging.info(f"Manifest directory: {manifest_dir.resolve()}")
    logging.info(f"Synthetic data directory: {synthetic_dir.resolve()}")
    logging.info(f"Output directory for merged files: {output_dir.resolve()}")
    
    # Load manifest mapping (conversation_id -> key_companies)
    manifest_mapping = load_manifest_mapping(run_id, manifest_dir)
    logging.info(f"Loaded manifest mapping for {len(manifest_mapping)} conversations.")
    
    # Merge the manifest data into synthetic data files
    merge_manifest_into_synthetic(run_id, synthetic_dir, output_dir, manifest_mapping)

if __name__ == "__main__":
    main()
