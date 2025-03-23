# Changes to Fix Docker Container Issues

## Problem Description

The Docker container was failing with the error: `ERROR - Error: Unknown LLM provider: vertex_ai`. This occurred because:

1. The container was trying to use the Vertex AI provider but the necessary packages weren't properly installed
2. The Dockerfile was configured to use Vertex AI by default even when no credentials were available

## Solution Overview

We've made the following improvements to fix these issues:

### 1. Enhanced Dockerfile

- Improved dependency installation to ensure all Google Cloud packages are correctly installed
- Created a smart entrypoint script that automatically selects between mock and Vertex AI providers
- Added an environment variable (`USE_MOCK_PROVIDER`) to control provider selection
- Implemented proper error handling for missing credentials

### 2. New and Improved Scripts

- **test_docker.sh**: Tests the Docker container with both mock and Vertex AI providers
- **setup_credentials.py**: Helps users set up and verify Google Cloud credentials
- **docker-entrypoint.sh**: Smart entrypoint that automatically selects the appropriate provider

### 3. Updated Documentation

- Updated README.md with clearer instructions for Docker usage
- Added a dedicated troubleshooting guide for Docker issues (`docs/docker_troubleshooting.md`)
- Improved error handling and user feedback in the Docker container

## How to Use

### Running with Mock Provider (No Credentials Required)

The Docker container now defaults to using the mock LLM provider, which doesn't require any Google Cloud credentials:

```bash
docker build -t chat-factory .
docker run -it --rm -v $(pwd):/app chat-factory
```

### Running with Vertex AI (Real Credentials)

To use Vertex AI instead of the mock provider, mount your service account key and set the environment variable:

```bash
docker run -it --rm \
  -v $(pwd):/app \
  -v /path/to/your/google-service-account.json:/app/google-service-account.json \
  -e USE_MOCK_PROVIDER=false \
  chat-factory
```

## Verification Process

You can verify the Docker setup using the test script:

```bash
# Test with mock provider only
./test_docker.sh

# Test with both mock and Vertex AI
./test_docker.sh path/to/credentials.json
```

## Future Improvements

1. Add environment variables for more configuration options (model name, project ID, etc.)
2. Implement better error messages for authentication failures
3. Create a Docker Compose file for easier configuration
4. Add support for multiple Google Cloud projects and regions