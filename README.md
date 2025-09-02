# Chat Factory: Modular Synthetic Conversation Generator

## Overview

Chat Factory is a modular framework for generating synthetic chat conversations for different use cases. It supports multiple conversation types including financial advisory discussions and company tagging scenarios. The framework uses a strategy pattern to separate different concerns and make it easy to extend for new use cases.

## Architecture

The framework is built around the following key components:

1. **Strategies**: Implementations of different processing approaches:
   - **Taxonomy Strategies**: Handle taxonomy loading and topic selection
   - **Generation Strategies**: Handle prompt construction and response processing
   - **Few-Shot Example Strategies**: Handle the selection and formatting of examples

2. **Models**: Core data structures used throughout the framework:
   - `Conversation`: Represents a single conversation
   - `ConversationFile`: Represents a file containing multiple conversations
   - `Taxonomy`: Represents a topic taxonomy

3. **LLM Providers**: Abstraction layer for language model services:
   - `VertexAIProvider`: Integration with Google Vertex AI and GenAI.
   - `MockLLMProvider`: Mock provider for testing without API credentials.

4. **Configuration**: Flexible configuration system supporting different use cases:
   - `BaseConfig`: Common configuration settings
   - Use-case specific config files (e.g., `financial_advisory.py`)

## Getting Started

### Installation

```bash
# Install dependencies
poetry install
```

### Running the Generator

The primary way to run the generator is by using the `run.sh` script. This script handles logging, directory setup, and running the selected use case.

To run a specific use case, edit the `RUN_FILE` variable at the top of the `run.sh` script:

```bash
# in run.sh
RUN_FILE="run_financial_advisory.py"
```

Then, execute the script:

```bash
./run.sh
```

## Available Use Cases

This framework is designed to be easily adapted for different use cases. The following use cases are currently implemented:

### Financial Advisory

*   **Runner Script:** `run_financial_advisory.py`
*   **Description:** Generates conversations between financial advisors and their ultra-high-net-worth clients. The conversations cover a wide range of financial topics, including investments, retirement planning, tax strategies, estate planning, and trust management.

### Company Tagging

*   **Runner Script:** `run_company_tagging.py`
*   **Description:** Generates conversations that are rich with mentions of specific companies. This use case is designed to create training data for named entity recognition (NER) models that need to identify company names in text. The conversations are focused on topics like company news, earnings reports, and stock performance.

### Voice of the Customer (VOC)

*   **Runner Script:** `run_voc.py`
*   **Description:** Generates "Voice of the Customer" conversations for the insurance industry. This use case simulates interactions between insurance brokers and life insurance wholesalers, providing insights into customer needs, concerns, and feedback.

## Sample Output

Each generated file contains a JSON object with a list of conversations. Here is an example of a single conversation:

```json
{
  "version": "5",
  "advisor": "Advisor Name",
  "client": "Client Name", 
  "conversations": [
    {
      "conversation_id": "run_id_1_12345678",
      "timestamp": "2025-03-23T14:30:00.000Z",
      "category": "Market Commentary",
      "topic": "Recent Market Performance",
      "lines": [
        {"speaker": "1", "text": "Hello, how can I help you today?"},
        {"speaker": "0", "text": "I'm interested in discussing recent market trends."}
      ]
    }
  ]
}
```

## Extending the Framework

To add a new use case:

1. Create new strategy implementations for your use case.
2. Register your new strategies in the `chat_factory/strategies/__init__.py` file.
3. Create a new configuration file for your use case in the `configs/` directory.
4. Create a new `run_*.py` script for your use case.

## Additional Tools

- **Metrics Analysis**: Analyze generated conversations with `scripts/metrics.py`
- **Post-Processing**: Apply additional processing with `scripts/post_processing_add_company_entities.py`

## Docker Support

Chat Factory can be easily run inside a Docker container, providing consistent execution across different environments.

### Building and Running

```bash
# Build the Docker image
docker build -t chat-factory .

# Run with volume mounting (to save generated data locally)
docker run -it --rm -v $(pwd):/app chat-factory
```

### Choosing Different Use Cases with Docker

You can select different use cases using the `USE_CASE` environment variable:

```bash
# Run the financial advisory use case with the mock provider
docker run --rm -e USE_CASE=financial_advisory -e USE_MOCK_PROVIDER=true \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "financial_run" --num 10

# Run the company tagging use case with the real Vertex AI provider
docker run --rm -e USE_CASE=company_tagging -e USE_MOCK_PROVIDER=false \
  -v $(pwd)/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "company_vertex_run" --num 10
```
