#!/usr/bin/env python3
"""
Main entry point for Chat Factory.
"""

import asyncio
import argparse
import importlib.util
import sys
import os
from pathlib import Path


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Chat Factory - Synthetic Conversation Generator')
    parser.add_argument("--run_id", type=str, help="Optional run ID to use for this generation")
    parser.add_argument("--config", type=str, default="config.py", 
                       help="Path to config file to use instead of default config.py")
    return parser.parse_args()


def load_config_module(file_path: str):
    """Load a Python module from file path."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    
    module_name = f"_config_{Path(file_path).stem}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    return config_module


async def run():
    """Run the chat factory."""
    args = parse_arguments()
    
    # Import main from the chat_factory package
    from chat_factory.main import main as chat_factory_main
    
    # Run the main function
    await chat_factory_main()


if __name__ == "__main__":
    asyncio.run(run())