# Docker Setup for Chat Factory

This document explains how to use Docker with the Chat Factory project, including how to configure for different LLM providers.

## Building the Docker Image

To build the Docker image, run:

```bash
docker build -t chat-factory:latest .
```

## Running the Container

### With Mock Provider (for testing)

To run the container with the mock LLM provider (no credentials needed):

```bash
docker run --rm -e USE_MOCK_PROVIDER=true \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "my_test_run" --num 5
```

### With Vertex AI Provider (for production)

To run with Vertex AI, you need Google Cloud credentials:

```bash
docker run --rm -e USE_MOCK_PROVIDER=false \
  -v /path/to/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "production_run" --num 20
```

### Running Different Use Cases

The container supports multiple use cases through the `USE_CASE` environment variable:

#### Company Tagging Use Case

```bash
docker run --rm -e USE_CASE=company_tagging -e USE_MOCK_PROVIDER=false \
  -v /path/to/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "company_tagging_run" --num 10
```

#### Company Tagging with Mock Provider

```bash
docker run --rm -e USE_CASE=company_tagging -e USE_MOCK_PROVIDER=true \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "company_tagging_mock_run" --num 5
```

#### Using Gemini 2.0 Configurations

```bash
docker run --rm -e USE_CASE=financial_advisory_gemini2 -e USE_MOCK_PROVIDER=false \
  -v /path/to/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "gemini2_run" --num 15
```

## Environment Variables

The container accepts these environment variables:

- `USE_MOCK_PROVIDER`: Set to `true` to use the mock LLM provider, `false` to use Vertex AI
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to the Google service account key inside the container (default: `/app/google-service-account.json`)
- `USE_CASE`: The use case to run (default: `financial_advisory`). Other supported values include `company_tagging`, etc.

## Volume Mounts

The container uses these volume mounts:

- `/app/output`: For logs and output files
- `/app/synthetic_data`: For generated synthetic conversation data
- `/app/google-service-account.json`: For Google Cloud credentials

## Building and Testing

For convenience, you can use the included build and test script:

```bash
./build_and_test_docker.sh
```

This will:
1. Build the Docker image
2. Test with the mock provider
3. If a service-account-key.json file exists, test with Vertex AI

## Troubleshooting

If you encounter issues:

1. **ImportError with vertexai**: This may happen if you're running an older version of the Google Cloud SDK. The Docker container is configured to install both the older Vertex AI SDK and the newer GenAI SDK.

2. **Authentication errors**: Make sure your service account has the necessary permissions for Vertex AI.

3. **Container exits immediately**: Check the logs with `docker logs [container_id]`. This may indicate a configuration issue.

4. **No output files generated**: Ensure volume mounts are correct and the container has write permissions.

For more detailed logging, you can check the logs in the output directory:

```bash
cat output/logs/synthetic_chat_generator.log
```