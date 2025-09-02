# Strategies Directory README

This directory is the core of the `chat-factory` framework's modularity. It contains the implementations of the different strategies that are used to control the conversation generation process.

## Overview of the Strategy Pattern

The `chat-factory` uses a strategy pattern to encapsulate different algorithms and behaviors for various parts of the generation process. This makes the framework highly extensible and allows for easy customization for new use cases without modifying the main generation logic.

At a high level, the `SyntheticChatGenerator` is the context class that uses several strategy objects. Each strategy object is responsible for a specific part of the generation process.

## Core Strategy Components (The Base Classes)

The `strategies/base/` directory contains the abstract base classes for each type of strategy. These base classes define the common interface that all concrete strategy implementations must adhere to.

### `TaxonomyStrategy`

*   **Purpose:** This strategy is responsible for handling the taxonomies that define the topics and structure of the conversations.
*   **Key Responsibilities:**
    *   Loading and parsing taxonomy files (e.g., `taxonomies/financial_advisory.json`).
    *   Flattening the taxonomy into a list of selectable topics.
    *   Selecting a topic for each conversation based on a configured distribution (e.g., uniform, weighted).

### `GenerationStrategy`

*   **Purpose:** This is the main workhorse strategy, responsible for constructing the prompt for the LLM and processing its response.
*   **Key Responsibilities:**
    *   Creating a "manifest blueprint" that outlines the parameters for a single conversation (e.g., topic, number of messages, key companies to mention).
    *   Constructing the detailed prompt that is sent to the LLM, combining the manifest blueprint, few-shot examples, and other instructions.
    *   Processing the raw text response from the LLM and parsing it into a structured format (`List[Dict[str, str]]`).

### `FewShotExampleStrategy`

*   **Purpose:** This strategy is responsible for selecting and formatting few-shot examples that are included in the prompt to guide the LLM's response.
*   **Key Responsibilities:**
    *   Loading few-shot examples from the `few_shot_examples/` directory.
    *   Selecting a relevant subset of examples based on the conversation's topic and category.
    *   Formatting the selected examples for inclusion in the final prompt.

### `DatetimeStrategy`

*   **Purpose:** This strategy is responsible for generating timestamps for the conversations and messages, allowing for the simulation of different temporal distributions.
*   **Key Responsibilities:**
    *   Generating a timestamp for each conversation based on a configured distribution (e.g., business hours, uniform).
    *   Generating timestamps for each message within a conversation to simulate realistic delays.

## Use-Case Specific Implementations

The real power of the strategy pattern comes from the ability to create concrete implementations of these base strategies for different use cases. The `financial_advisory/` and `company_tagging/` directories contain examples of such implementations.

For example:

*   **`financial_advisory/taxonomy_strategy.py`:** Implements the `TaxonomyStrategy` to handle the hierarchical structure of the `financial_advisory.json` taxonomy.
*   **`company_tagging/generation_strategy.py`:** Implements the `GenerationStrategy` with specific logic for constructing prompts that instruct the LLM to include mentions of specific companies.

By creating a new set of strategy implementations, you can completely change the behavior of the conversation generator to fit a new use case.

## How to Add a New Use-Case Strategy

To add a new set of strategies for a new use case, you need to:

1.  **Create a new directory:** Create a new directory in `strategies/` for your new use case (e.g., `strategies/my_new_use_case/`).

2.  **Implement the strategy classes:** In the new directory, create Python files for each strategy you need to customize. Each class should inherit from the appropriate base class in `strategies/base/` and implement the required methods.

    ```python
    # strategies/my_new_use_case/generation_strategy.py

    from ..base import GenerationStrategy

    class MyNewGenerationStrategy(GenerationStrategy):
        def construct_prompt(self, ...):
            # Your custom prompt construction logic here
            ...
    ```

3.  **Register the new strategies:** In `strategies/__init__.py`, import your new strategy classes and add them to the corresponding registry dictionaries.

    ```python
    # strategies/__init__.py

    from .my_new_use_case import MyNewGenerationStrategy

    GENERATION_STRATEGIES: Dict[str, Type[GenerationStrategy]] = {
        "financial_advisory": FinancialAdvisoryGenerationStrategy,
        "company_tagging": CompanyTaggingGenerationStrategy,
        "my_new_strategy": MyNewGenerationStrategy
    }
    ```

4.  **Update the configuration:** In your use-case-specific configuration file (in the `configs/` directory), set the appropriate strategy variable to the name of your new strategy.

    ```python
    # configs/my_new_use_case.py

    GENERATION_STRATEGY = "my_new_strategy"
    ```