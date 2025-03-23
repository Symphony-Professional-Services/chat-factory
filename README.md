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
   - `VertexAIProvider`: Integration with Google Vertex AI and GenAI (supports both Gemini 1.5 and 2.0)
   - `MockLLMProvider`: Mock provider for testing without API credentials

4. **Configuration**: Flexible configuration system supporting different use cases:
   - `BaseConfig`: Common configuration settings
   - Use-case specific config files (e.g., `financial_advisory.py`)

## Getting Started

### Installation

```bash
# Install dependencies
poetry install

# Or alternatively
pip install -e .
```

### Running the Generator

```bash
# Run the financial advisory generator with Vertex AI (Gemini 1.5)
./run_financial_advisory.py --num 10

# Run the financial advisory generator with Gemini 2.0
./run_financial_advisory_gemini2.py --run_id "gemini2_test" --num 10

# Or use the shell script that handles logging and setup
./run.sh
```

### Configuration

The framework is highly configurable. Each use case has its own configuration file in the `configs/` directory:

- `configs/financial_advisory.py`: Configuration for financial advisory use case with Gemini 1.5
- `configs/company_tagging.py`: Configuration for company tagging use case
- `configs/gemini_config.py`: Configuration for using Gemini 2.0 models

## Available Use Cases

### Financial Advisory

Generates conversations between financial advisors and their clients, covering topics like:

- Financial Goals & Planning
- Market Commentary
- Product & Service Inquiry
- Small Talk
- Client Personal Concerns

### Company Tagging (Coming Soon)

Generates conversations that include specific company mentions for training entity recognition systems, covering:

- Trade discussions
- Deal negotiations
- Stock analysis
- Market updates
- News on specific companies
- Earnings reports discussions

## Extending the Framework

To add a new use case:

1. Create new strategy implementations:
   - Create a taxonomy strategy that knows how to process your taxonomy format
   - Create a generation strategy that knows how to create prompts and process responses
   - Optionally create a few-shot example strategy if you need special handling

2. Register your strategies in the factory:
   - Add your strategies to the registry in `chat_factory/strategies/__init__.py`

3. Create a configuration file:
   - Add a new file in `configs/` with your use case's settings

## Additional Tools

- **Metrics Analysis**: Analyze generated conversations with `metrics.py`
- **Post-Processing**: Apply additional processing with `post_processing_add_company_entities.py`

## Docker Support

Chat Factory can be easily run inside a Docker container, providing consistent execution across different environments.

### Testing and Setup

We provide scripts to help you test and set up Docker:

```bash
# Test your Docker setup 
./test_docker.sh

# Set up Google Cloud credentials
./setup_credentials.py
```

See [Docker Troubleshooting Guide](docs/docker_troubleshooting.md) for detailed help with Docker issues.

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
# Run company tagging use case
docker run --rm -e USE_CASE=company_tagging \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "company_run" --num 10

# Run financial advisory with Gemini 2.0
docker run --rm -e USE_CASE=financial_advisory_gemini2 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "gemini2_run" --num 5

# Run with Vertex AI (real provider)
docker run --rm -e USE_CASE=company_tagging -e USE_MOCK_PROVIDER=false \
  -v $(pwd)/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "company_vertex_run" --num 3
```

Available use cases:
- `financial_advisory` (default)
- `company_tagging`
- `financial_advisory_gemini2`
- `company_tagging_gemini2`

For detailed information on all use cases, see [Use Cases Documentation](docs/use_cases.md).

### Common Run Script Parameters

All run scripts support these common parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--run_id` | Unique identifier for this generation run | `--run_id "financial_test_20250323"` |
| `--num` | Number of conversations to generate | `--num 50` |
| `--config` | Path to config file (some scripts) | `--config configs/company_tagging.py` |
| `--use_mock` | Use mock LLM provider for testing | `--use_mock` |

Example with multiple parameters:
```bash
docker run -it --rm -v $(pwd):/app chat-factory poetry run python run_company_tagging.py \
  --run_id "quarterly_dataset_q1" \
  --num 100 \
  --config configs/company_tagging_gemini2.py
```

### Creating Custom Docker Run Scripts

For production use, you can create custom run scripts:

1. Create a custom shell script (e.g., `custom_run.sh`):
   ```bash
   #!/bin/bash
   
   # Generate a unique run ID
   RUN_ID="custom_$(date +"%Y_%m_%d_%H%M%S")"
   
   # Set up directories
   mkdir -p synthetic_data output/logs few_shot_examples conversation_scripts
   chmod -R 777 synthetic_data output few_shot_examples conversation_scripts
   
   # Run your specific use case
   poetry run python run_company_tagging.py --run_id "$RUN_ID" --num 50
   ```

2. Make it executable and use it with Docker:
   ```bash
   chmod +x custom_run.sh
   docker run -it --rm -v $(pwd):/app chat-factory ./custom_run.sh
   ```

### Environment Variables and Credentials

#### Running with Mock Provider (No Credentials Required)

By default, the Docker container uses the mock LLM provider, which doesn't require any Google Cloud credentials:

```bash
docker run -it --rm \
  -v $(pwd):/app \
  chat-factory
```

#### Running with Vertex AI (Real Credentials)

To use Vertex AI instead of the mock provider, mount your service account key and set the `USE_MOCK_PROVIDER` environment variable to `false`:

```bash
docker run -it --rm \
  -v $(pwd):/app \
  -v /path/to/your/google-service-account.json:/app/google-service-account.json \
  -e USE_MOCK_PROVIDER=false \
  chat-factory
```

**Important**: The container looks for a service account file named `google-service-account.json`. If your file has a different name, update the `GOOGLE_APPLICATION_CREDENTIALS` environment variable:

```bash
docker run -it --rm \
  -v $(pwd):/app \
  -v /path/to/your/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  -e USE_MOCK_PROVIDER=false \
  chat-factory
```

#### Forcing a Specific Provider

You can explicitly control which provider to use with these environment variables:

* Force mock provider: `-e USE_MOCK_PROVIDER=true`
* Force Vertex AI provider: `-e USE_MOCK_PROVIDER=false`

Example with additional parameters:
```bash
docker run -it --rm \
  -v $(pwd):/app \
  -v /path/to/your/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  -e USE_MOCK_PROVIDER=false \
  chat-factory \
  --run_id "vertex_test" --num 5
```

### Troubleshooting Docker Deployments

#### Common Issues

**Error: "name 'vertexai' is not defined" or "Unknown LLM provider: vertex_ai"**

If you encounter errors related to Vertex AI in your Docker logs:
```
ERROR - Error initializing AI service: name 'vertexai' is not defined
ERROR - Error: Unknown LLM provider: vertex_ai
```

These errors typically occur when:
1. You're trying to use Vertex AI but don't have the necessary packages installed, or
2. You're trying to use Vertex AI but don't have valid credentials mounted

Solutions:

1. **Use the updated Dockerfile** which includes:
   - Better dependency installation
   - Automatic provider selection based on available credentials
   - A smart entrypoint script that switches between providers

2. **Rebuild your Docker image** with the latest changes:
   ```bash
   docker build --no-cache -t chat-factory .
   ```

3. **Run with mock provider** if you don't have valid credentials:
   ```bash
   docker run -it --rm -v $(pwd):/app chat-factory
   ```

4. **Run with real credentials** if you have them:
   ```bash
   docker run -it --rm \
     -v $(pwd):/app \
     -v /path/to/credentials.json:/app/google-service-account.json \
     -e USE_MOCK_PROVIDER=false \
     chat-factory
   ```

5. **Check your credential file** with a verification command:
   ```bash
   docker run -it --rm \
     -v $(pwd):/app \
     -v /path/to/credentials.json:/app/google-service-account.json \
     --entrypoint bash \
     chat-factory \
     -c "ls -la /app/google-service-account.json && cat /app/google-service-account.json | grep type"
   ```
   This should show the file permissions and confirm it's a service account key file.

6. **Manually install packages** inside the container if needed:
   ```bash
   docker run -it --rm -v $(pwd):/app --entrypoint bash chat-factory
   pip install --upgrade vertexai google-cloud-aiplatform google-genai
   exit
   # Then run your container normally
   ```

### Creating a Custom Docker Image

You can create your own Docker image with a different default run script:

1. Create a custom Dockerfile:
   ```dockerfile
   FROM python:3.10-slim-buster
   
   # Set working directory
   WORKDIR /app
   
   # Install Poetry
   RUN pip install --no-cache-dir poetry
   
   # Copy dependencies first (for better layer caching)
   COPY pyproject.toml poetry.lock* ./
   RUN poetry install --no-root --no-interaction --only main
   
   # Copy the rest of the application
   COPY . .
   
   # Make your custom run script executable
   RUN chmod +x custom_run_company_tagging.sh
   
   # Use your custom script as the entry point
   ENTRYPOINT ["sh", "/app/custom_run_company_tagging.sh"]
   ```

2. Build and run your custom image:
   ```bash
   docker build -t chat-factory-company-tagging -f Dockerfile.company_tagging .
   docker run -it --rm -v $(pwd):/app chat-factory-company-tagging
   ```

This approach is useful when you have different teams running different use cases.

### Accessing Generated Data and Outputs

When running with Docker using volume mounting, the generated data will be available in these directories:

- **Generated Conversations**: `./synthetic_data/{RUN_ID}/`
- **Conversation Manifests**: `./conversation_scripts/`
- **Logs**: `./output/logs/`

Each conversation file is stored in JSON format and follows this structure:
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

To process these files, you can use the built-in tools:
```bash
# Run metrics analysis on generated data
docker run -it --rm -v $(pwd):/app chat-factory poetry run python metrics.py --run_id "your_run_id"
```

## Future Improvements

- Additional use cases beyond financial advisory and company tagging
- Support for more LLM providers
- Interactive conversation generation
- Extended analytics and visualization tools
- Enhanced test coverage
- Support for multimodal content with Gemini 2.0

### THIS COMMAND WORKS
docker run --rm -e USE_MOCK_PROVIDER=false -v
      $(pwd)/service-account-key.json:/app/google-service-account.json -v $(pwd)/output:/app/output -v
      $(pwd)/synthetic_data:/app/synthetic_data chat-factory:latest --run_id "vertexai_test" --num 1




### THIS WORKS ACTUALLY:
docker run --rm -e USE_CASE=financial_advisory_gemini2 -e USE_MOCK_PROVIDER=false   -v $(pwd)/service-account-key.json:/app/google-service-account.json   -v $(pwd)/output:/app/output   -v $(pwd)/synthetic_data:/app/synthetic_data   chat-factory:latest --run_id "company_vertex_run"