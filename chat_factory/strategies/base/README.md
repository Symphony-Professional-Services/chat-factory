# Base Strategies README

This directory contains the abstract base classes (ABCs) for the strategy pattern used in the `chat-factory` framework. These base classes define the common interface that all concrete strategy implementations must adhere to, ensuring consistency and modularity.

## Overview

The purpose of these base classes is to define a contract for what each type of strategy should do. By using abstract methods, we can enforce that any new strategy implementation provides the necessary functionality, which makes the framework more robust and easier to extend.

## Core Base Strategies

### `taxonomy_strategy.py`

*   **Class:** `TaxonomyStrategy`
*   **Purpose:** This strategy is responsible for handling the taxonomies that define the topics and structure of the conversations.
*   **Abstract Methods:**
    *   `load_taxonomy()`: Defines how to load and parse a taxonomy file.
    *   `flatten_taxonomy()`: Defines how to convert the raw taxonomy data into a flat list of selectable topics.
    *   `select_topic()`: Defines the logic for selecting a topic from the flattened list for each conversation.
    *   `detect_taxonomy_format()`: Defines how to detect the format of a given taxonomy file.

### `generation_strategy.py`

*   **Class:** `GenerationStrategy`
*   **Purpose:** This is the main workhorse strategy, responsible for constructing the prompt for the LLM and processing its response.
*   **Abstract Methods:**
    *   `create_manifest_blueprint()`: Defines how to create a blueprint of the conversation to be generated, including parameters like topic, number of messages, and any special requirements.
    *   `construct_prompt()`: Defines the logic for building the final prompt string that will be sent to the LLM.
    *   `process_llm_response()`: Defines how to parse the raw text response from the LLM into a structured format.

### `few_shot_strategy.py`

*   **Class:** `FewShotExampleStrategy`
*   **Purpose:** This strategy is responsible for selecting and formatting few-shot examples to be included in the prompt, which helps to guide the LLM's response.
*   **Abstract Methods:**
    *   `get_examples()`: Defines the logic for selecting a relevant subset of examples from the `few_shot_examples/` directory based on the conversation's topic and category.
    *   `format_examples()`: Defines how to format the selected examples for inclusion in the final prompt.
    *   `load_example_file()`: Defines how to load a single few-shot example from a file.

### `datetime_strategy.py`

*   **Class:** `DatetimeStrategy`
*   **Purpose:** This strategy is responsible for generating timestamps for the conversations and messages, allowing for the simulation of different temporal distributions.
*   **Abstract Methods:**
    *   `generate_conversation_timestamp()`: Defines how to generate a timestamp for each conversation based on a configured distribution (e.g., business hours, uniform).
    *   `generate_message_timestamps()`: Defines how to generate timestamps for each message within a conversation to simulate realistic delays.
    *   `get_message_count_distribution()`: Defines how to get the distribution of conversations over a given time period.

## How to Use the Base Strategies

These base classes are not meant to be used directly. Instead, they should be subclassed to create concrete strategy implementations for specific use cases.

For example, the `CompanyTaggingGenerationStrategy` in `strategies/company_tagging/generation_strategy.py` inherits from `GenerationStrategy` and implements the `construct_prompt` method with specific logic for creating prompts that include company names.

By subclassing these base strategies, you can create new behaviors and extend the framework for new use cases without modifying the core generation logic.
