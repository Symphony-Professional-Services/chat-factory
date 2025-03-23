FROM python:3.10-slim-buster

# Set working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching)
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Install Google Cloud and vertexai dependencies globally (outside of Poetry)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir vertexai google-cloud-aiplatform google-api-python-client protobuf google-genai

# Install the application dependencies (but not the application itself yet)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction

# Copy the rest of the application
COPY . .

# Install the application in development mode
RUN pip install -e .

# Make run.sh and other scripts executable
RUN chmod +x run.sh run_*.py

# Default to mock provider if no credentials 
ENV USE_MOCK_PROVIDER=true
# Default use case (can be financial_advisory, company_tagging, etc.)
ENV USE_CASE=financial_advisory

# Credentials path is set at runtime, not build time
# The path is now configured in the entrypoint script

# Create an entrypoint script with provider selection logic
RUN echo '#!/bin/bash\n\
# Set the credentials path if not already set\n\
export GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-/app/google-service-account.json}\n\
\n\
# Get the use case from environment variable or default to financial_advisory\n\
USE_CASE=${USE_CASE:-financial_advisory}\n\
echo "Running use case: $USE_CASE"\n\
\n\
# check if USE_MOCK_PROVIDER is true or if credentials file does not exist\n\
if [ "$USE_MOCK_PROVIDER" = "true" ] || [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then\n\
    echo "Using mock LLM provider..."\n\
    # Update config files to use mock provider\n\
    if grep -q "LLM_PROVIDER" /app/configs/${USE_CASE}.py 2>/dev/null; then\n\
        sed -i '\''s/LLM_PROVIDER = "vertex_ai"/LLM_PROVIDER = "mock"/'\'' /app/configs/${USE_CASE}.py\n\
    else\n\
        sed -i '\''s/# LLM Settings/# LLM Settings\\nLLM_PROVIDER = "mock"/'\'' /app/configs/${USE_CASE}.py\n\
    fi\n\
    \n\
    # Check if the specific mock script exists, otherwise fall back to run_financial_advisory_mock.py\n\
    if [ -f "/app/run_${USE_CASE}_mock.py" ]; then\n\
        echo "Running: python run_${USE_CASE}_mock.py with args: $@"\n\
        exec python "run_${USE_CASE}_mock.py" "$@"\n\
    else\n\
        echo "Mock script for ${USE_CASE} not found, using financial_advisory as fallback"\n\
        exec python run_financial_advisory_mock.py "$@"\n\
    fi\n\
else\n\
    echo "Using Vertex AI provider with credentials at $GOOGLE_APPLICATION_CREDENTIALS"\n\
    # Make sure config uses vertex_ai provider\n\
    if grep -q "LLM_PROVIDER" /app/configs/${USE_CASE}.py 2>/dev/null; then\n\
        sed -i '\''s/LLM_PROVIDER = "mock"/LLM_PROVIDER = "vertex_ai"/'\'' /app/configs/${USE_CASE}.py\n\
    else\n\
        sed -i '\''s/# LLM Settings/# LLM Settings\\nLLM_PROVIDER = "vertex_ai"/'\'' /app/configs/${USE_CASE}.py\n\
    fi\n\
    \n\
    # Print Python path and packages for debugging\n\
    echo "Python path: $(which python)"\n\
    echo "Installed packages:"\n\
    pip list | grep -E "vertexai|google-cloud-aiplatform|google-genai"\n\
    \n\
    # Check if the specific script exists, otherwise fall back to run_financial_advisory.py\n\
    if [ -f "/app/run_${USE_CASE}.py" ]; then\n\
        echo "Running: python run_${USE_CASE}.py with args: $@"\n\
        exec python "run_${USE_CASE}.py" "$@"\n\
    else\n\
        echo "Script for ${USE_CASE} not found, using financial_advisory as fallback"\n\
        exec python run_financial_advisory.py "$@"\n\
    fi\n\
fi' > /app/docker-entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Set the command to run when the container starts
ENTRYPOINT ["/app/docker-entrypoint.sh"]