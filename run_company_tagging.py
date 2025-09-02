#!/usr/bin/env python3
"""
Runner script for company tagging use case with Gemini 2.0.

This script generates synthetic conversations with company mentions using the Gemini 2.0
models via the GenAI SDK for improved entity recognition.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
import uuid
import asyncio

from main import SyntheticChatGenerator
from configs import company_tagging_gemini2 as config


def setup_logging(log_file, run_id):
    """Set up logging configuration."""
    log_dir = os.path.join("output", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_path = os.path.join(log_dir, f"{log_file.replace('.log', '')}_{run_id}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"Logging initialized. Log file: {log_path}")


def setup_output_directories(config, run_id):
    """Set up output directories for generated data."""
    # Create main output directory
    output_dir = os.path.join(config.OUTPUT_DIR, run_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create conversation scripts directory
    conversation_dir = os.path.join(config.CONVERSATION_MANIFEST_DIR, run_id)
    os.makedirs(conversation_dir, exist_ok=True)
    
    logging.info(f"Output directories created: {output_dir}, {conversation_dir}")
    return output_dir, conversation_dir


async def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate synthetic conversations with company tagging using Gemini 2.0")
    parser.add_argument("--run_id", type=str, help="Unique run identifier")
    parser.add_argument("--num", type=int, help="Number of conversations to generate")
    
    args = parser.parse_args()
    
    # Set run_id if provided, otherwise generate one
    run_id = args.run_id if args.run_id else f"{config.RUN_ID_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Set number of conversations if provided
    if args.num:
        config.NUM_CONVERSATIONS = args.num
    
    # Setup logging and directories
    setup_logging(config.LOG_FILE, run_id)
    setup_output_directories(config, run_id)
    
    # Log configuration and run information
    logging.info(f"Starting company tagging generation with Gemini 2.0")
    logging.info(f"Run ID: {run_id}")
    logging.info(f"Number of conversations: {config.NUM_CONVERSATIONS}")
    logging.info(f"Model: {config.MODEL_NAME}")
    logging.info(f"Using GenAI SDK: {config.USE_GENAI_SDK}")
    
    try:
        # Create and run the generator
        generator = SyntheticChatGenerator(config=config)
        generator.run_id = run_id
        
        # Initialize the generator and generate conversations
        await generator.initialize()
        await generator.generate_synthetic_data()
        
        logging.info(f"Generation completed successfully")
        
    except Exception as e:
        logging.error(f"Error during generation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())