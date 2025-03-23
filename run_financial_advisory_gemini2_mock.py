#!/usr/bin/env python3
"""
Runner script for financial advisory use case with Gemini 2.0 and mock LLM.
This is useful for testing without needing actual Vertex AI credentials.
"""

import asyncio
import argparse
import sys
import logging


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Financial Advisory Chat Generator (Gemini 2.0 Mock)')
    parser.add_argument("--run_id", type=str, help="Optional run ID to use for this generation")
    parser.add_argument("--num", type=int, default=3, help="Number of conversations to generate")
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Import from the new framework
        from chat_factory.config import load_config_from_file
        from chat_factory.llm import create_llm_provider
        from chat_factory.strategies import (
            create_taxonomy_strategy,
            create_generation_strategy,
            create_few_shot_strategy
        )
        from chat_factory.generator import SyntheticChatGenerator
        
        # Load the financial advisory gemini2 config
        config = load_config_from_file("configs/financial_advisory_gemini2.py")
        
        # Force mock provider
        config.LLM_PROVIDER = "mock"
        
        # Update config with command line arguments
        if args.run_id:
            config.RUN_ID = args.run_id
        
        if args.num:
            config.NUM_CONVERSATIONS = args.num
        
        # Create the strategies
        taxonomy_strategy = create_taxonomy_strategy(config.TAXONOMY_STRATEGY, config)
        generation_strategy = create_generation_strategy(config.GENERATION_STRATEGY, config)
        few_shot_strategy = create_few_shot_strategy(config.FEW_SHOT_STRATEGY, config)
        llm_provider = create_llm_provider(config.LLM_PROVIDER, config)
        
        # Create the generator
        generator = SyntheticChatGenerator(
            config=config,
            taxonomy_strategy=taxonomy_strategy,
            generation_strategy=generation_strategy,
            few_shot_strategy=few_shot_strategy,
            llm_provider=llm_provider
        )
        
        # Run the generator
        logging.info(f"Starting financial advisory conversation generation with mock LLM (Gemini 2.0 config)")
        await generator.generate_synthetic_data()
        logging.info(f"Completed conversation generation")
        
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())