# Financial Advisory Strategies README

This directory contains the concrete strategy implementations for the **financial advisory** use case. These strategies are designed to generate realistic synthetic conversations between financial advisors and their clients.

## A Use-Case-Specific Implementation

This set of strategies is a prime example of how the `chat-factory` framework is designed to be extended for specific use cases. Similar to the `company_tagging` strategies, the strategies in this directory inherit from the base strategy classes and implement the specific logic required for the financial advisory domain.

By encapsulating the use-case-specific logic in this directory, we keep the core generation framework clean and focused, while allowing for easy customization and extension.

## `FinancialAdvisoryTaxonomyStrategy`

*   **Purpose:** This strategy is responsible for handling the `financial_advisory.json` taxonomy file.
*   **Key Responsibilities:**
    *   **Loading the Taxonomy:** It loads the taxonomy file, which contains a hierarchical structure of financial advisory topics, including categories, topics, and subtopics.
    *   **Flattening the Taxonomy:** It flattens the hierarchical taxonomy into a simple list of topics that can be easily selected from.
    *   **Topic Selection:** It selects a topic for each conversation from the flattened list, ensuring a wide variety of conversation topics.

## `FinancialAdvisoryGenerationStrategy`

*   **Purpose:** This strategy is responsible for constructing the prompts that instruct the LLM to generate financial advisory conversations.
*   **Key Responsibilities:**
    *   **Prompt Construction:** It constructs a detailed prompt that includes the selected topic, as well as other parameters like the advisor's persona and the desired communication style.
    *   **Company Mention (Optional):** This strategy can also optionally include company mentions in the conversations, demonstrating how strategies can be configured to handle different scenarios within the same use case.
    *   **Response Processing:** It processes the LLM's response to extract the generated conversation and format it into the standard data structure.

## How it Works

1.  The `FinancialAdvisoryTaxonomyStrategy` loads the `financial_advisory.json` taxonomy and selects a topic (e.g., "Market Commentary/Inflation").
2.  The `FinancialAdvisoryGenerationStrategy` creates a manifest blueprint for the conversation, which may or may not include a company to be mentioned, based on the configuration.
3.  The `FinancialAdvisoryGenerationStrategy` then constructs a prompt that instructs the LLM to generate a conversation about the selected topic, with the specified persona and style.
4.  The LLM generates a conversation based on the prompt.
5.  The `FinancialAdvisoryGenerationStrategy` processes the LLM's response and creates the final conversation object.
