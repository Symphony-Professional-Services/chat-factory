# LLM Directory README

This directory contains the abstraction layer for interacting with different Large Language Models (LLMs).

## Overview

The `llm` package is designed to make the `chat-factory` framework independent of any specific LLM provider. It uses a provider pattern, with a base class that defines a common interface for all LLM providers.

## Components

### `base.py`

This file defines the `LLMProvider` abstract base class. It specifies the methods that all LLM providers must implement, such as:

*   `initialize()`: To set up the client and any necessary connections.
*   `generate_content()`: To generate content from a prompt.
*   `retry_with_backoff()`: To handle API rate limits and other transient errors.

By programming to this interface, the rest of the application can remain agnostic to the specific LLM provider being used.

### `mock.py`

This file contains the `MockLLMProvider`, which is a fake implementation of the `LLMProvider` interface. It returns predefined responses and is used for:

*   **Local Development:** Allows developers to work on the application without needing to have API credentials for a real LLM provider.
*   **Testing:** Enables fast and predictable unit and integration tests.

### `vertex_ai.py`

This file contains the `VertexAIProvider`, which is the implementation of the `LLMProvider` interface for Google's Gemini models via the Vertex AI SDK. It includes:

*   Logic to handle both the GenAI and Vertex AI SDKs.
*   Authentication with Google Cloud.
*   Robust error handling and retry logic with exponential backoff.

## How to Add a New LLM Provider

To add support for a new LLM provider, you need to:

1.  **Create a new provider class:** Create a new Python file in the `llm/` directory and define a new class that inherits from `LLMProvider`.

2.  **Implement the required methods:** Implement all the abstract methods defined in the `LLMProvider` base class (`initialize`, `generate_content`, `retry_with_backoff`).

3.  **Register the new provider:** In `llm/__init__.py`, import your new provider class and add it to the `LLM_PROVIDERS` dictionary.

    ```python
    # llm/__init__.py

    from .my_new_provider import MyNewProvider

    LLM_PROVIDERS: Dict[str, Type[LLMProvider]] = {
        "mock": MockLLMProvider,
        "vertex_ai": VertexAIProvider,
        "my_new_provider": MyNewProvider
    }
    ```

4.  **Update the configuration:** In your use-case-specific configuration file, set the `LLM_PROVIDER` variable to the name of your new provider.

    ```python
    # configs/my_new_use_case.py

    LLM_PROVIDER = "my_new_provider"
    ```
