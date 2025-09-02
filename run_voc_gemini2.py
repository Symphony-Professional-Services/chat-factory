#!/usr/bin/env python3
"""
# --- EDITABLE SECTION START ---
This script is for generating voice of customer synthetic data for the nationwide use case looking at brokers and life insurance wholesalers

This script orchestrates the generation of synthetic data based on the defined configuration
and generation strategies.
# --- EDITABLE SECTION END ---
"""

# --- BOILERPLATE START ---
# Standard library imports
import os
import sys
import logging
import argparse
import asyncio
from datetime import datetime
from importlib import import_module # Used for dynamic config loading (like Script 2)

# --- BOILERPLATE END ---

# --- EDITABLE SECTION START - IMPORT/CONFIG=COMPLETE ---
# TODO: Import the specific generator class and configuration loading mechanism.
# Option 1: Direct Import (like Script 1)
# from main import SyntheticChatGenerator
# from configs import my_specific_config as config

# Option 2: Framework/Factory Import (like Script 2)
# Ensure the 'chat_factory' or your specific framework is installed/available
try:
    from chat_factory.config import load_config_from_file
    from chat_factory.generator import SyntheticChatGenerator
    from chat_factory.llm import create_llm_provider
    from chat_factory.strategies import (
        create_taxonomy_strategy,
        create_generation_strategy,
        create_few_shot_strategy
    )
    # Add other necessary strategy imports if applicable
    # from chat_factory.strategies.datetime_distribution.factory import create_datetime_strategy
    FRAMEWORK_AVAILABLE = True
except ImportError:
    logging.warning("Chat Factory framework not found. Assuming a different generator structure.")
    # Define a placeholder if needed, or ensure your generator is imported differently
    class SyntheticChatGenerator: # Placeholder
         def __init__(self, *args, **kwargs): pass
         async def initialize(self): pass
         async def generate_synthetic_data(self): pass
    FRAMEWORK_AVAILABLE = False
    # If not using the framework, ensure your specific Generator class is imported above.

# TODO: Define default configuration path if using dynamic loading.
DEFAULT_CONFIG_PATH = "" # e.g., "configs.financial_advisory_gemini2"

# TODO: Define default run ID prefix.
DEFAULT_RUN_ID_PREFIX = "synthetic_run"
# --- EDITABLE SECTION END ---


# --- BOILERPLATE START ARGUMENT PARSER=COMPLETE---
def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Synthetic Data Generation Runner") # Generic description
    parser.add_argument("--run_id", type=str, default=None,
                        help="Unique identifier for this generation run. If None, one is generated.")
    parser.add_argument("--num", type=int, default=None,
                        help="Number of items (e.g., conversations) to generate. Overrides config if set.")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_PATH,
                        help=f"Python module path to the configuration file (e.g., 'configs.my_config'). Default: {DEFAULT_CONFIG_PATH}")
    parser.add_argument("--output_dir", type=str, default="output",
                        help="Base directory for logs and generated data.")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging level.")
    # --- BOILERPLATE END ---

    # --- EDITABLE SECTION START ---
    # TODO: Add any task-specific command-line arguments here.
    # parser.add_argument("--specific_param", type=str, help="Description of task-specific parameter.")
    # --- EDITABLE SECTION END ---

    # --- BOILERPLATE START ---
    return parser.parse_args()
    # --- BOILERPLATE END ---


# --- BOILERPLATE START ---
def setup_logging(log_level, log_dir, run_id):
    """Set up logging configuration."""
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"{run_id}.log"
    log_path = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout) # Log to console as well
        ]
    )
    # Reduce verbosity for noisy libraries if needed
    # logging.getLogger("some_noisy_library").setLevel(logging.WARNING)

    logging.info(f"Logging initialized. Level: {logging.getLevelName(log_level)}. Log file: {log_path}")
    return logging.getLogger() # Return root logger
# --- BOILERPLATE END ---


# --- BOILERPLATE START ---
def setup_output_directories(base_output_dir, run_id):
    """Set up output directories for the run."""
    run_output_dir = os.path.join(base_output_dir, run_id)
    logs_dir = os.path.join(base_output_dir, "logs") # Keep logs separate from run-specific output
    # --- BOILERPLATE END ---

    # --- EDITABLE SECTION START DIRECTORY SETUP=COMPLETE---
    # TODO: Define and create specific subdirectories needed for this task's output.
    # Example: conversation manifests, raw data, processed data etc.
    # conversation_manifest_dir = os.path.join(base_output_dir, "conversation_manifests", run_id)
    raw_data_dir = os.path.join(run_output_dir, "raw_data")

    os.makedirs(run_output_dir, exist_ok=True)
    os.makedirs(raw_data_dir, exist_ok=True)
    # os.makedirs(conversation_manifest_dir, exist_ok=True)

    logging.info(f"Run-specific output directory: {run_output_dir}")
    # logging.info(f"Conversation manifest directory: {conversation_manifest_dir}")
    logging.info(f"Raw data directory: {raw_data_dir}")

    # Return paths needed by the generator or main logic
    return logs_dir, run_output_dir, raw_data_dir #, conversation_manifest_dir
    # --- EDITABLE SECTION END ---


# --- BOILERPLATE START ---
async def main():
    """Main execution function."""
    args = parse_arguments()

    # Determine Run ID
    run_id = args.run_id if args.run_id else f"{DEFAULT_RUN_ID_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Setup Output Directories (Logs dir needed for setup_logging)
    logs_dir, run_output_dir, raw_data_dir = setup_output_directories(args.output_dir, run_id) # Adjust return values based on setup_output_directories

    # Setup Logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(log_level, logs_dir, run_id)

    logger.info(f"Starting run ID: {run_id}")
    logger.info(f"Using configuration path: {args.config}")

    try:
        # --- BOILERPLATE END ---

        # --- EDITABLE SECTION START MAIN FN=INCOMPLETE ---
        # TODO: Load the configuration module [COMPLETE]
        try:
            # Assumes config path is like 'folder.subfolder.module_name'
            config_module_path = args.config.replace("/", ".").replace(".py", "")
            config = import_module(config_module_path)
            logger.info(f"Successfully loaded configuration from: {config_module_path}")
        except ImportError as e:
            logger.error(f"Failed to import configuration module '{args.config}': {e}", exc_info=True)
            sys.exit(1)

        # TODO: Override configuration parameters with command-line arguments if provided. [COMPLETE]
        if args.num is not None:
            logger.info(f"Overriding NUM_CONVERSATIONS/ITEMS from config with command-line value: {args.num}")
            config.NUM_CONVERSATIONS = args.num # Or config.NUM_ITEMS, etc. - adapt to your config variable name
        else:
             # Ensure the variable exists in the config, provide a default if necessary
             if not hasattr(config, 'NUM_CONVERSATIONS'):
                 logger.warning("NUM_CONVERSATIONS not found in config, using default value 10.")
                 config.NUM_CONVERSATIONS = 10 # Example default

        # TODO: Add run_id and potentially other dynamic info to the config object if needed by the generator. [COMPLETE]
        setattr(config, 'RUN_ID', run_id)
        setattr(config, 'RUN_OUTPUT_DIR', run_output_dir)
        setattr(config, 'RAW_DATA_DIR', raw_data_dir)
        # setattr(config, 'CONVERSATION_MANIFEST_DIR', conversation_manifest_dir) # If using this

        # TODO: Log key configuration parameters. Adapt these to your specific config values. [COMPLETE]
        logger.info(f"Task: {getattr(config, 'TASK_NAME', '<Not Specified>')}") # Example: Add TASK_NAME to your config
        logger.info(f"Number of items to generate: {config.NUM_CONVERSATIONS}") # Adapt variable name
        logger.info(f"Using Model: {getattr(config, 'MODEL_NAME', '<Not Specified>')}")
        logger.info(f"Using GenAI SDK: {getattr(config, 'USE_GENAI_SDK', '<Not Specified>')}")

        # TODO: Instantiate the Generator. Adapt based on your generator's needs. []
        # Option 1: Simple instantiation (like Script 1)
        # generator = SyntheticChatGenerator(config=config)
        # generator.run_id = run_id # Or pass run_id during init if supported

        # Option 2: Instantiation with strategies (like Script 2, requires framework)
        if FRAMEWORK_AVAILABLE: # Check if the framework components were imported
            logger.info("Using Chat Factory framework: Creating strategies...")
            try:
                # Create necessary providers and strategies based on the config
                llm_provider = create_llm_provider(config.PROVIDER, config)
                taxonomy_strategy = create_taxonomy_strategy(config.TAXONOMY_STRATEGY, config)
                generation_strategy = create_generation_strategy(config.GENERATION_STRATEGY, config)
                few_shot_strategy = create_few_shot_strategy(config.FEW_SHOT_STRATEGY, config)

                # Optional: Add other strategies like datetime
                datetime_strategy = None
                if hasattr(config, 'DATETIME_STRATEGY') and config.DATETIME_STRATEGY:
                     # from chat_factory.strategies.datetime_distribution.factory import create_datetime_strategy # Import here or globally
                     datetime_strategy = create_datetime_strategy(config)
                     logger.info(f"Using datetime strategy: {config.DATETIME_STRATEGY}")

                # Instantiate the generator with strategies
                generator = SyntheticChatGenerator(
                    config=config, # Pass the modified config object
                    taxonomy_strategy=taxonomy_strategy,
                    generation_strategy=generation_strategy,
                    few_shot_strategy=few_shot_strategy,
                    llm_provider=llm_provider,
                    datetime_strategy=datetime_strategy # Pass None if not used
                    # Add other strategies as needed
                )
                logger.info("Strategies created and generator instantiated.")
            except AttributeError as e:
                 logger.error(f"Missing configuration required for strategy creation: {e}", exc_info=True)
                 sys.exit(1)
            except Exception as e:
                 logger.error(f"Error creating strategies or generator: {e}", exc_info=True)
                 sys.exit(1)
        # THIS IS A FALLBACK TO BASIC STRUCTURE USING THE CONFIG [COMPLETE] [EVALUATE WHAT A GOOD FALLBACK STRATEGY WOULD BE FOR GENERIC GENERATION - MAYBE IT PROMPTS THE USE TO GET THE INFO?]
        else:
            logger.info("WARNING: FRAMEWORK NOT DETECTED")
            # # Fallback or non-framework generator instantiation
            #  logger.info("Framework not detected. Using basic generator instantiation.")
            #  try:
            #      # Ensure your non-framework SyntheticChatGenerator is imported correctly
            #      from main import SyntheticChatGenerator # Example fallback import
            #      generator = SyntheticChatGenerator(config=config)
            #      # Manually set run_id if needed and not handled by constructor
            #      # generator.run_id = run_id
            #  except ImportError:
            #       logger.error("Could not import a suitable SyntheticChatGenerator class.")
            #       sys.exit(1)
            #  except Exception as e:
            #      logger.error(f"Error instantiating the generator: {e}", exc_info=True)
            #      sys.exit(1)

        # TODO: Call the main generation method(s). Adapt method names as needed.
        logger.info(f"Starting generation process...")

        # If your generator has an initialization step (like Script 1) [COMPLETE - may not be necessary]
        if hasattr(generator, 'initialize') and asyncio.iscoroutinefunction(generator.initialize):
             logger.info("Running async initialization...")
             await generator.initialize()
             logger.info("Initialization complete.")

        # Call the main generation function
        await generator.generate_synthetic_data()

        logger.info(f"Generation completed successfully for run {run_id}")
        # --- EDITABLE SECTION END ---

    # --- BOILERPLATE START ---
    except Exception as e:
        logger.error(f"An error occurred during the generation process for run {run_id}: {e}", exc_info=True)
        sys.exit(1) # Exit with a non-zero code to indicate failure

# --- BOILERPLATE END ---


# --- BOILERPLATE START ---
if __name__ == "__main__":
    # Ensureuvloop is installed and imported for potential performance gains with asyncio
    try:
        import uvloop
        uvloop.install()
        logging.info("Using uvloop for asyncio event loop.")
    except ImportError:
        logging.info("uvloop not found, using standard asyncio event loop.")
        pass # uvloop is optional

    asyncio.run(main())
# --- BOILERPLATE END ---