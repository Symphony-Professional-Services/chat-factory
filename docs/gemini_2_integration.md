# Gemini 2.0 Integration Guide

This document explains how to use Gemini 2.0 models with the Chat Factory framework.

## Overview

The Chat Factory framework has been updated to support Gemini 2.0 models through the Google GenAI SDK, while maintaining backward compatibility with Gemini 1.5 models. This update allows you to take advantage of the improved capabilities in Gemini 2.0 without changing your existing code or configuration structure.

## How It Works

The `VertexAIProvider` has been enhanced to support both Gemini 1.5 (via Vertex AI SDK) and Gemini 2.0 (via GenAI SDK) models. The provider automatically selects the appropriate SDK based on the model name and configuration, providing a seamless experience regardless of which model you choose.

### Key Features

- **Automatic SDK Selection**: The provider can automatically detect if you're using a Gemini 2.0 model and use the appropriate SDK.
- **Graceful Fallback**: If the GenAI SDK is not available, it will fall back to the Vertex AI SDK.
- **Unified Interface**: The same LLM provider interface is used for both SDKs, making it easy to switch between models.
- **Explicit Configuration**: You can explicitly set which SDK to use with the `USE_GENAI_SDK` configuration parameter.

## Setup

1. Install the Google GenAI SDK:

```bash
pip install google-genai
# Or with Poetry
poetry add google-genai
```

2. Update your configuration to use a Gemini 2.0 model:

```python
# Google Cloud Configuration
PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.0-flash-001"  # Gemini 2.0 model
API_VERSION = "v1"  # API version for GenAI SDK
```

3. Optionally, explicitly set which SDK to use:

```python
USE_GENAI_SDK = True  # Force using the GenAI SDK
```

## Available Gemini 2.0 Models

- `gemini-2.0-flash-001`: Fast, cost-effective model for most general use cases
- `gemini-2.0-pro-001`: High-performance model for complex reasoning and generation

## Configuration Parameters

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `MODEL_NAME` | The name of the model to use | `gemini-1.5-flash-002` | `gemini-2.0-flash-001` |
| `API_VERSION` | API version for the GenAI SDK | `v1` | `v1` |
| `USE_GENAI_SDK` | Explicitly use the GenAI SDK | `None` (auto-detect) | `True` |

## Example Configuration

Here's an example configuration for using Gemini 2.0 with the financial advisory use case:

```python
# Google Cloud Configuration
PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.0-flash-001"  # Using Gemini 2.0 model
API_VERSION = "v1"  # API version for GenAI SDK
USE_GENAI_SDK = True  # Explicitly use the GenAI SDK

# LLM Settings
TEMPERATURE = 0.7
TOP_P = 0.95
TOP_K = 40

# Provider Selection
PROVIDER = "vertex_ai"  # Still use the same provider name

# Strategy Selection (unchanged)
TAXONOMY_STRATEGY = "financial_advisory"
GENERATION_STRATEGY = "financial_advisory"
FEW_SHOT_STRATEGY = "basic"

# ... rest of your configuration
```

## Running with Gemini 2.0

You can use the dedicated runner script for Gemini 2.0 or adapt your existing scripts:

```bash
# Using the dedicated financial advisory Gemini 2.0 runner
./run_financial_advisory_gemini2.py --run_id "gemini2_test" --num 10

# Or using a standard runner with the Gemini 2.0 config
python run_financial_advisory.py --config configs/financial_advisory_gemini2.py --run_id "gemini2_test"
```

## Authentication

The GenAI SDK uses the same authentication methods as the Vertex AI SDK. Make sure your environment is properly set up:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

## Troubleshooting

- **ImportError**: Make sure you have installed the `google-genai` package.
- **Authentication Errors**: Verify your credentials are properly set up.
- **Model Not Found**: Confirm that your project has access to Gemini 2.0 models.
- **API Version**: If you encounter API compatibility issues, try explicitly setting `API_VERSION = "v1"`.

## Differences Between SDKs

The provider handles the differences between the SDKs internally, but there are some notable changes:

- The GenAI SDK format for generation configuration is different.
- The GenAI SDK's `generate_content` method is not natively async, so we use `asyncio.to_thread`.
- Response formats differ: GenAI SDK provides results in `response.text` while Vertex AI SDK uses `response.candidates[0].content.text`.

These differences are all handled automatically by the provider.