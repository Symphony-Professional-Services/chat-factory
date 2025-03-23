#!/usr/bin/env python
"""
Script to run company tagging generation with the new framework.
"""

import logging
import asyncio
import sys
import argparse
from importlib import import_module
from pathlib import Path

from chat_factory.strategies import (
    create_taxonomy_strategy,
    create_generation_strategy,
    create_few_shot_strategy
)
from chat_factory.llm import create_llm_provider
from chat_factory.generator import SyntheticChatGenerator


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run company tagging generation")
    parser.add_argument("--config", type=str, default="configs.company_tagging",
                       help="Python module with configuration")
    parser.add_argument("--run_id", type=str, default=None,
                       help="Optional run ID for this generation batch")
    parser.add_argument("--use_mock", action="store_true",
                       help="Use mock LLM provider for testing")
    args = parser.parse_args()
    
    # Load configuration module
    config_module = import_module(args.config)
    config = config_module
    
    # Override configuration with command line args
    if args.run_id:
        config.RUN_ID = args.run_id
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"Starting company tagging conversation generation with config: {args.config}")
    
    # Use mock provider if requested
    if args.use_mock:
        llm_provider_name = "mock"
        logging.info("Using mock LLM provider")
    else:
        llm_provider_name = config.LLM_PROVIDER
    
    # Create strategies
    taxonomy_strategy = create_taxonomy_strategy(config.TAXONOMY_STRATEGY, config)
    generation_strategy = create_generation_strategy(config.GENERATION_STRATEGY, config)
    few_shot_strategy = create_few_shot_strategy(config.FEW_SHOT_STRATEGY, config)
    llm_provider = create_llm_provider(llm_provider_name, config)
    
    # Create generator
    generator = SyntheticChatGenerator(
        config=config,
        taxonomy_strategy=taxonomy_strategy,
        generation_strategy=generation_strategy,
        few_shot_strategy=few_shot_strategy,
        llm_provider=llm_provider
    )
    
    # Generate conversations
    await generator.generate_synthetic_data()
    
    logging.info("Completed company tagging conversation generation")


if __name__ == "__main__":
    asyncio.run(main())