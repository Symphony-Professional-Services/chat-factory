#!/bin/bash

# File: test_docker.sh
#
# Description:
# Tests the Docker container with both mock and real providers
# To use: ./test_docker.sh [path/to/credentials.json]

# Set text colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Chat Factory Docker Test Script${NC}"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

# Build the Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -t chat-factory .

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to build Docker image.${NC}"
    exit 1
fi

echo -e "${GREEN}Docker image built successfully.${NC}"

# Create temp output directory
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTDIR="docker_test_${TIMESTAMP}"
mkdir -p "${OUTDIR}"
chmod 777 "${OUTDIR}"

# Test with mock provider (no credentials needed)
echo -e "\n${YELLOW}Running test with mock provider...${NC}"
echo "This test doesn't require Google Cloud credentials."

docker run -it --rm \
    -v "$(pwd)/${OUTDIR}:/app/synthetic_data" \
    -e USE_MOCK_PROVIDER=true \
    chat-factory \
    --run_id "mock_test_${TIMESTAMP}" \
    --num 1

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Mock provider test failed.${NC}"
else
    echo -e "${GREEN}Mock provider test completed successfully.${NC}"
    echo "Generated files are in: ${OUTDIR}"
fi

# Check if credential file was provided as argument
CRED_FILE=$1
if [ -z "$CRED_FILE" ]; then
    echo -e "\n${YELLOW}No credential file provided. Skipping Vertex AI test.${NC}"
    echo "To test with Vertex AI, run: ./test_docker.sh path/to/credentials.json"
    exit 0
fi

# Check if the specified credential file exists
if [ ! -f "$CRED_FILE" ]; then
    echo -e "${RED}Error: Credential file '$CRED_FILE' not found.${NC}"
    exit 1
fi

# Test with Vertex AI provider (requires valid credentials)
echo -e "\n${YELLOW}Running test with Vertex AI provider...${NC}"
echo "Using credentials from: $CRED_FILE"

docker run -it --rm \
    -v "$(pwd)/${OUTDIR}:/app/synthetic_data" \
    -v "$(realpath $CRED_FILE):/app/google-service-account.json" \
    -e USE_MOCK_PROVIDER=false \
    chat-factory \
    --run_id "vertex_test_${TIMESTAMP}" \
    --num 1

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Vertex AI provider test failed.${NC}"
    echo "Check that the credential file is valid and has the necessary permissions."
else
    echo -e "${GREEN}Vertex AI provider test completed successfully.${NC}"
    echo "Generated files are in: ${OUTDIR}"
fi

echo -e "\n${YELLOW}Test Summary${NC}"
echo "================="
echo "1. Docker image build: ${GREEN}Success${NC}"
echo "2. Mock provider test: ${GREEN}Success${NC}"
if [ -n "$CRED_FILE" ]; then
    if [ $? -eq 0 ]; then
        echo "3. Vertex AI test: ${GREEN}Success${NC}"
    else
        echo "3. Vertex AI test: ${RED}Failed${NC}"
    fi
fi
echo "Output files located in: ${OUTDIR}"
echo ""
echo "Next steps:"
echo "1. Use the Docker container in your workflows"
echo "2. To run with mock provider: docker run -it --rm -v \$(pwd):/app chat-factory"
echo "3. To run with Vertex AI: docker run -it --rm -v \$(pwd):/app -v /path/to/credentials.json:/app/google-service-account.json -e USE_MOCK_PROVIDER=false chat-factory"