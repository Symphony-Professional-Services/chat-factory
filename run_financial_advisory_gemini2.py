#!/usr/bin/env python
"""
Run financial advisory conversation generation using Gemini 2.0 models.
"""

import argparse
import logging
import os
import asyncio
import sys
from importlib import import_module


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate financial advisory conversations with Gemini 2.0")
    parser.add_argument("--run_id", help="Unique ID for this run", default="financial_advisory_gemini2")
    parser.add_argument("--num", type=int, help="Number of conversations to generate", default=None)
    parser.add_argument("--config", help="Path to config file", default="configs/financial_advisory_gemini2.py")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger()
    
    # Create output directories if they don't exist
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/logs", exist_ok=True)
    
    # Add file handler for logging
    file_handler = logging.FileHandler(f"output/logs/{args.run_id}.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    
    try:
        # Load the financial advisory gemini2 config
        config_path = args.config.replace("/", ".").replace(".py", "")
        config = import_module(config_path)
        
        # Import from the new framework
        from chat_factory.llm import create_llm_provider
        from chat_factory.strategies import (
            create_taxonomy_strategy,
            create_generation_strategy,
            create_few_shot_strategy
        )
        from chat_factory.generator import SyntheticChatGenerator
        
        # Add RUN_ID attribute to config if it's missing
        if not hasattr(config, 'RUN_ID'):
            setattr(config, 'RUN_ID', args.run_id)
            logging.info(f"Added RUN_ID to config: {args.run_id}")
        
        # Override config with command line arguments if provided
        if args.num:
            config.NUM_CONVERSATIONS = args.num
            
        logging.info(f"Generating {config.NUM_CONVERSATIONS} conversations with model {config.MODEL_NAME}")
        logging.info(f"Using GenAI SDK: {getattr(config, 'USE_GENAI_SDK', 'Auto-detect')}")
            
        # Create the strategies
        taxonomy_strategy = create_taxonomy_strategy(config.TAXONOMY_STRATEGY, config)
        generation_strategy = create_generation_strategy(config.GENERATION_STRATEGY, config)
        few_shot_strategy = create_few_shot_strategy(config.FEW_SHOT_STRATEGY, config)
        llm_provider = create_llm_provider(config.PROVIDER, config)
        
        # Create the generator
        generator = SyntheticChatGenerator(
            config=config,
            taxonomy_strategy=taxonomy_strategy,
            generation_strategy=generation_strategy,
            few_shot_strategy=few_shot_strategy,
            llm_provider=llm_provider
        )
        
        # Run the generator
        logging.info(f"Starting financial advisory conversation generation with Gemini 2.0")
        await generator.generate_synthetic_data()
        logging.info(f"Completed conversation generation")
        
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())