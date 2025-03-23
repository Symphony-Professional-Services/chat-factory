#!/bin/bash

# Create debug container that runs Python directly
docker run --rm \
  -v "$(pwd)/google-service-account.json:/app/google-service-account.json" \
  -e USE_MOCK_PROVIDER=false \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/google-service-account.json \
  --entrypoint bash \
  chat-factory-fixed \
  -c "cd /app && poetry run python -c \"
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Print environment info
print('\\nEnvironment Information:')
print(f'GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get(\\\"GOOGLE_APPLICATION_CREDENTIALS\\\")}')
print(f'File exists: {os.path.exists(os.environ.get(\\\"GOOGLE_APPLICATION_CREDENTIALS\\\", \\\"\\\"))}')

# Try to import packages
print('\\nPackage Imports:')
try:
    import vertexai
    print('vertexai: ✓')
except ImportError as e:
    print(f'vertexai: ✗ - {e}')

try:
    import google.cloud.aiplatform
    print('google.cloud.aiplatform: ✓')
except ImportError as e:
    print(f'google.cloud.aiplatform: ✗ - {e}')

try:
    import google.genai
    print('google.genai: ✓')
except ImportError as e:
    print(f'google.genai: ✗ - {e}')

# Try to initialize LLM provider
print('\\nTrying to initialize Vertex AI provider:')
try:
    from chat_factory.llm import create_llm_provider
    
    # Create a mock config object
    class Config:
        PROJECT_ID = 'sk-ml-inference'
        LOCATION = 'us-central1'
        MODEL_NAME = 'gemini-1.5-flash-002'
        TEMPERATURE = 0.3
        TOP_P = 1.0
        TOP_K = 40
    
    config = Config()
    
    # Try to create LLM provider
    print('Creating LLM provider...')
    provider = create_llm_provider(\\'vertex_ai\\', config)
    print('Provider created, initializing...')
    
    # Try to initialize (will be async)
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(provider.initialize())
    print('Successfully initialized Vertex AI provider!')
    
    # Try a simple generation
    print('\\nTesting content generation:')
    prompt = 'Write a brief greeting'
    response = loop.run_until_complete(provider.generate_content(prompt))
    print(f'Response: {response[:100]}...')
    
except Exception as e:
    import traceback
    print(f'Error: {e}')
    traceback.print_exc()
\""