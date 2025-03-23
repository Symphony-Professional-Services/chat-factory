# Gemini 2.0 Setup Guide

This guide will help you set up and use the Gemini 2.0 models with the Chat Factory framework.

## Prerequisites

- Google Cloud account with Vertex AI API enabled
- Project with Gemini API access
- Python 3.10+

## Installation

1. Install the required dependencies:

```bash
pip install google-genai
```

2. Set up environment variables:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

## Configuration

Edit the configuration file in `configs/gemini_config.py` to customize your generation settings:

```python
# LLM settings
PROVIDER = "genai"  # Use the GenAI provider for Gemini 2.0
MODEL_NAME = "gemini-2.0-flash-001"  # Available models: gemini-2.0-flash-001, gemini-2.0-pro-001
TEMPERATURE = 0.7
TOP_P = 0.95
TOP_K = 40
API_VERSION = "v1"
```

## Running the Generator

```bash
python run_gemini.py --run_id "your_run_id" --num_conversations 10
```

## Available Gemini 2.0 Models

| Model | Description | Best for |
|-------|-------------|----------|
| gemini-2.0-flash-001 | Fast, cost-effective model with improved performance | Most general use cases, chat applications |
| gemini-2.0-pro-001 | High-performance model with enhanced capabilities | Complex reasoning, code generation, detailed analysis |

## Troubleshooting

- **Authentication errors**: Ensure your `GOOGLE_APPLICATION_CREDENTIALS` is correctly set
- **Model not available**: Check that your Google Cloud project has access to Gemini models
- **Rate limits**: Implement backoff/retry logic (already included in the provider)

## Differences from Gemini 1.5

- New API structure and response format
- Improved performance and capabilities
- Different safety categories
- Support for multimodal live API and generation

## Migrating from Vertex AI to GenAI

If you were previously using the `vertex_ai` provider, update your configuration:

```python
# Old configuration
PROVIDER = "vertex_ai"
MODEL_NAME = "gemini-1.5-flash-002"

# New configuration
PROVIDER = "genai"
MODEL_NAME = "gemini-2.0-flash-001"
API_VERSION = "v1"
```