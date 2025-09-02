"""
Main entry point for the Chat Factory.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from .config import load_config_from_file
from .utils import setup_logging
from .llm import create_llm_provider
from .strategies import (
    create_taxonomy_strategy, 
    create_generation_strategy,
    create_few_shot_strategy
)
from .generator import SyntheticChatGenerator


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Chat Factory - Synthetic Conversation Generator')
    parser.add_argument("--run_id", type=str, help="Optional run ID to use for this generation")
    parser.add_argument("--config", type=str, default="config.py", 
                       help="Path to config file to use instead of default config.py")
    return parser.parse_args()


async def main():
    """Main application entry point."""
    args = parse_arguments()
    
    try:
        # Load configuration
        config = load_config_from_file(args.config)
        
        # Override run_id if provided
        if args.run_id:
            config.RUN_ID = args.run_id
            
        # Setup logging
        logger = setup_logging(config.LOG_FILE, config.RUN_ID)
        logger.info(f"Starting Chat Factory with config from {args.config}")
        
        # Create strategies
        taxonomy_strategy = create_taxonomy_strategy(config.TAXONOMY_STRATEGY, config)
        generation_strategy = create_generation_strategy(config.GENERATION_STRATEGY, config)
        few_shot_strategy = create_few_shot_strategy(config.FEW_SHOT_STRATEGY, config)
        llm_provider = create_llm_provider(config.LLM_PROVIDER, config)
        
        # Create generator
        generator = SyntheticChatGenerator(
            config=config,
            taxonomy_strategy=taxonomy_strategy,
            generation_strategy=generation_strategy,
            few_shot_strategy=few_shot_strategy,
            llm_provider=llm_provider
        )
        
        # Run generation
        await generator.generate_synthetic_data()
        
        logger.info("Synthetic data generation completed successfully")
        
    except Exception as e:
        logging.error(f"Error in Chat Factory: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())