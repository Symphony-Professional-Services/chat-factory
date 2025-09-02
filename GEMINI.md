# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the `chat-factory` project.

## Project Overview

`chat-factory` is a modular Python framework for generating synthetic chat conversations for different use cases. It leverages a strategy pattern to easily support new conversation types. The main supported use cases are:

*   **Financial Advisory**: Generates conversations between financial advisors and clients.
*   **Company Tagging**: Generates conversations that include mentions of specific companies, useful for training NER models.

The framework is built to work with Large Language Models, specifically Google's Gemini 1.5 and 2.0 models via the Vertex AI SDK, but also includes a mock provider for local testing.

The project is managed with `poetry` and is fully dockerized, allowing for consistent execution environments.

## File Structure

```
/home/sean/repos/chat-factory/
├───chat_factory/            # Core application source code
│   ├───config/              # Configuration loading and management
│   ├───llm/                 # LLM provider abstractions (Vertex AI, Mock)
│   ├───models/              # Pydantic data models for conversations
│   ├───strategies/          # Core logic for different generation strategies
│   └───utils/               # Helper functions and utilities
├───configs/                 # Use-case specific configuration files
├───data/                    # Data files, like company lists
├───docs/                    # Project documentation
├───few_shot_examples/       # Few-shot examples for the LLM prompts
├───output/                  # Output directory for logs
├───scripts/                 # Helper scripts for building, testing, etc.
├───synthetic_data/          # Output directory for generated conversations
├───taxonomies/              # Taxonomy files for different use cases
├───tests/                   # Unit and integration tests
├───main.py                  # Main entry point for the application
├───run_*.py                 # Runner scripts for specific use cases
├───Dockerfile               # Dockerfile for building the container
├───pyproject.toml           # Project dependencies and metadata
└───README.md                # Project README file
```

## Information Workflow and Architecture

### Information Flow

The generation process follows these steps:

1.  **Initialization**: A runner script (e.g., `run_financial_advisory.py`) is executed. This script loads a use-case-specific configuration file from the `configs/` directory.

2.  **Strategy Creation**: Based on the configuration, the appropriate strategies (Taxonomy, Generation, Few-Shot) are created.

3.  **Generator Initialization**: The `SyntheticChatGenerator` is initialized with the configuration and strategies.

4.  **Taxonomy Loading**: The `TaxonomyStrategy` loads the appropriate taxonomy from the `taxonomies/` directory.

5.  **Conversation Loop**: The `SyntheticChatGenerator` enters a loop to generate the requested number of conversations.

6.  **Topic Selection**: In each iteration, the `TaxonomyStrategy` selects a topic from the loaded taxonomy.

7.  **Manifest Blueprint Creation**: The `GenerationStrategy` creates a "manifest blueprint", which is a dictionary describing the conversation to be generated (e.g., topic, number of messages, key companies).

8.  **Few-Shot Example Loading**: The `FewShotExampleStrategy` loads relevant few-shot examples from the `few_shot_examples/` directory.

9.  **Prompt Construction**: The `GenerationStrategy` constructs a detailed prompt for the LLM, including the manifest blueprint and few-shot examples.

10. **LLM Call**: The `LLMProvider` sends the prompt to the language model (Vertex AI or mock) and receives the generated conversation.

11. **Response Processing**: The `GenerationStrategy` processes the LLM's response, parsing it into a `SingleConversation` object.

12. **Saving**: The generated conversation is added to a buffer and periodically saved to a file in the `synthetic_data/` directory.

### Architectural Components

*   **Runners (`run_*.py`)**: These are the main entry points for the application. Each runner is responsible for loading a specific configuration and starting the generation process.
*   **Configurations (`configs/*.py`)**: These files define all the parameters for a specific use case, including which strategies to use, the location of data files, and LLM settings.
*   **Generator (`chat_factory/generator.py`)**: This is the main orchestrator. It manages the conversation generation loop, calls the various strategies, and saves the output.
*   **Strategies (`chat_factory/strategies/`)**: This is the core of the framework's modularity. Different strategies can be plugged in to change the generation behavior without modifying the core generator logic.
    *   **TaxonomyStrategy**: Handles loading and selecting topics from a taxonomy.
    *   **GenerationStrategy**: Responsible for creating the prompt and processing the LLM response.
    *   **FewShotExampleStrategy**: Provides few-shot examples to guide the LLM.
*   **LLM Providers (`chat_factory/llm/`)**: This layer abstracts the interaction with the language model, making it easy to switch between different providers (e.g., from a mock provider to the real Vertex AI provider).
*   **Data Models (`chat_factory/models/`)**: Pydantic models are used to ensure that the data structures for conversations, chat lines, etc., are consistent throughout the application.

### Switching Between Use Cases

The framework is designed to be easily extensible for new use cases. To switch between the "financial advisory" and "company tagging" use cases, the following components are changed:

*   **Configuration File**: The primary change is the configuration file loaded by the runner. For example, `run_financial_advisory.py` loads `configs/financial_advisory_gemini2.py`, while `run_company_tagging.py` would load a corresponding `configs/company_tagging.py`.

*   **Taxonomy File**: Each use case has its own taxonomy file in the `taxonomies/` directory. The "financial advisory" use case uses `taxonomies/financial_advisory.json`, which defines conversation topics related to finance. The "company tagging" use case would use a different taxonomy that defines conversation types where company mentions are relevant.

*   **Generation Strategy**: While both use cases might share a base generation strategy, they can have specialized implementations. The "company tagging" use case, for example, has a generation strategy that is aware of companies and how to inject them into the conversation.

*   **Few-Shot Examples**: Each use case has its own set of few-shot examples in the `few_shot_examples/` directory. These examples are tailored to the specific type of conversation being generated.

By changing these components, the behavior of the generator can be significantly altered to produce different types of synthetic data, all while using the same core generation logic.

## Building and Running

### Local Development

**Installation:**

```bash
poetry install
```

**Running the generator:**

There are several scripts to run the different use cases:

```bash
# Run the financial advisory generator
./run_financial_advisory.py --run_id "test_run" --num 10

# Run the company tagging generator
./run_company_tagging.py --num 10
```

A general-purpose `run.sh` script is also available to handle logging and setup.

### Docker

The project is dockerized for easy and consistent execution.

**Building the image:**

```bash
docker build -t chat-factory .
```

**Running the container:**

The `USE_CASE` environment variable controls which conversation type is generated.

```bash
# Run the default financial_advisory use case with the mock provider
docker run --rm -e USE_CASE=financial_advisory \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "test_run" --num 5

# Run the company tagging use case with the real Vertex AI provider
docker run --rm -e USE_CASE=company_tagging -e USE_MOCK_PROVIDER=false \
  -v $(pwd)/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "company_vertex_run" --num 3
```

## Development Conventions

*   **Configuration**: The project uses a flexible configuration system. Each use case has its own configuration file in the `configs/` directory.
*   **Strategies**: The core logic is organized into strategies (Taxonomy, Generation, Few-Shot Examples) to allow for easy extension. New strategies should be added to the `chat_factory/strategies/` directory.
*   **Data Models**: Core data structures are defined in `chat_factory/models/`.
*   **LLM Providers**: The `chat_factory/llm/` directory contains the abstraction layer for language model services.
*   **Testing**: The `scripts/build_and_test_docker.sh` script can be used to build and test the Docker container in both mock and Vertex AI modes.