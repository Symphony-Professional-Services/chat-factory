# Config Directory README

This directory is responsible for managing the configuration of the `chat-factory` application.

## Overview

The configuration system is designed to be flexible and allow for easy customization for different use cases. It uses a combination of a base configuration and use-case-specific configuration files to achieve this.

## Components

### `base_config.py`

This file defines the `BaseConfig` dataclass, which serves as a schema for all the possible configuration options in the framework. It includes settings for:

*   Project metadata (e.g., `PROJECT_ID`, `RUN_ID`)
*   LLM provider and parameters (e.g., `MODEL_NAME`, `TEMPERATURE`)
*   Output settings (e.g., `OUTPUT_DIR`, `JSON_VERSION`)
*   Generation parameters (e.g., `NUM_CONVERSATIONS`, `MIN_MESSAGES`)
*   Strategy selection (e.g., `TAXONOMY_STRATEGY`, `GENERATION_STRATEGY`)
*   File paths (e.g., `TAXONOMY_FILE`, `FEW_SHOT_EXAMPLES_DIR`)

By having a centralized base configuration, we ensure that all configurations are consistent and that all necessary parameters are accounted for.

### `config_loader.py`

This file contains the `load_config_from_file` function, which is responsible for loading the use-case-specific configuration files. It dynamically loads a Python file as a module and populates a `BaseConfig` object with the settings defined in that file.

## How to Add a New Configuration

To add a new configuration for a new use case, you need to:

1.  **Create a new configuration file:** Create a new Python file in the `configs/` directory (in the root of the project). This file should define the configuration variables for your new use case.

2.  **Set the configuration variables:** In your new configuration file, you only need to set the variables that are different from the defaults in `base_config.py`. For example:

    ```python
    # configs/my_new_use_case.py

    TAXONOMY_STRATEGY = "my_new_taxonomy_strategy"
    GENERATION_STRATEGY = "my_new_generation_strategy"
    TAXONOMY_FILE = "taxonomies/my_new_taxonomy.json"
    ```

3.  **Use the new configuration:** In your runner script, you can then load your new configuration file using the `load_config_from_file` function.
