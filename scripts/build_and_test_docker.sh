#!/bin/bash

# File: build_and_test_docker.sh
#
# Description:
# This script builds and tests the chat-factory Docker container
# with both mock mode and VertexAI mode.

set -e  # Exit on any error

echo "=== Building Chat Factory Docker Container ==="
docker build -t chat-factory:latest .

echo ""
echo "=== Testing with Mock Provider ==="
echo "Running container with mock provider..."
docker run --rm -e USE_MOCK_PROVIDER=true \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "mock_test" --num 2

echo ""
echo "=== Results of Mock Provider Test ==="
ls -la synthetic_data/
echo "Log file content:"
tail -n 20 output/logs/synthetic_chat_generator.log

echo ""
echo "=== Testing with VertexAI Provider ==="
echo "Note: This requires valid service account credentials"

if [ -f "service-account-key.json" ]; then
    echo "Found service account key, running with VertexAI provider..."
    docker run --rm -e USE_MOCK_PROVIDER=false \
      -v $(pwd)/service-account-key.json:/app/google-service-account.json \
      -v $(pwd)/output:/app/output \
      -v $(pwd)/synthetic_data:/app/synthetic_data \
      chat-factory:latest --run_id "vertexai_test" --num 2
    
    echo ""
    echo "=== Results of VertexAI Provider Test ==="
    ls -la synthetic_data/
    echo "Log file content:"
    tail -n 20 output/logs/synthetic_chat_generator.log
else
    echo "No service-account-key.json found, skipping VertexAI test."
    echo "To test with VertexAI, place your service account JSON file at ./service-account-key.json"
fi

echo ""
echo "=== Test Complete ==="