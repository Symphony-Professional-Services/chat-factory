# Docker Troubleshooting Guide for Chat Factory

## Issue: "name 'vertexai' is not defined" Error

### Problem Description
When running the Chat Factory Docker container with Vertex AI provider, users were encountering the following error:
```
name 'vertexai' is not defined
```

This occurred because the vertexai package was installed in the system Python environment but was not properly accessible when imported in the context of the Poetry virtual environment.

### Root Cause
1. The Python import system was failing to find the vertexai module despite it being installed
2. The try/except import mechanism in vertex_ai.py was catching the first ImportError but then failing on the next import attempt
3. There was a mismatch between the environment where packages were installed and where the code was running

### Solution
We implemented several changes to fix this issue:

1. **Modified vertex_ai.py file** to:
   - Initialize global variables for imports first
   - Handle import errors more gracefully
   - Add better error messages and logging
   - Validate SDK availability before usage
   - Provide clear instructions when dependencies are missing

2. **Updated Dockerfile** to:
   - Install system dependencies needed for package compilation
   - Install Google packages globally rather than in the Poetry environment
   - Configure Poetry to not create virtual environments (using system site packages)
   - Add debugging information to the entrypoint script
   - Use direct Python execution instead of Poetry run commands

3. **Updated configuration files** to explicitly include the LLM provider setting

4. **Created helper scripts** for building and testing the container

### Testing the Solution
The solution has been tested with both the mock provider and the Vertex AI provider:

1. **Mock Provider Test**: Successfully generated conversations without requiring credentials
2. **Vertex AI Provider Test**: Successfully connected to Google Cloud and generated conversations using the VertexAI provider

### Usage Instructions

#### With Mock Provider (for testing)
```bash
docker run --rm -e USE_MOCK_PROVIDER=true \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "my_test_run" --num 5
```

#### With Vertex AI Provider (for production)
```bash
docker run --rm -e USE_MOCK_PROVIDER=false \
  -v /path/to/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "production_run" --num 20
```

## Additional Troubleshooting Tips

If you encounter any further issues:

1. **Check logs**: Output logs are stored in `output/logs/synthetic_chat_generator.log`

2. **Verify credentials**: Make sure your service account has the necessary permissions for Vertex AI

3. **Package installation**: If you need to add or update packages, modify the Dockerfile to install them globally:
   ```dockerfile
   RUN pip install --no-cache-dir package-name
   ```

4. **Environment variables**: Use environment variables to control the container behavior:
   ```bash
   docker run -e ENV_VAR_NAME=value ...
   ```

5. **Debugging**: To get a shell in the container for debugging:
   ```bash
   docker run -it --entrypoint /bin/bash chat-factory:latest
   ```