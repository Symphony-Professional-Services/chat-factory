#!/bin/bash

# Fix the import issue in the Docker container
cat > fix_imports.py << EOF
#!/usr/bin/env python

# This script fixes the vertex_ai import issue
import sys
import os
import json

def fix_llm_init():
    """Fix the __init__.py file in the chat_factory/llm directory."""
    init_file = "chat_factory/llm/__init__.py"
    
    # Read the current content
    with open(init_file, "r") as f:
        content = f.read()
    
    # Check if we need to modify the file
    if "MockLLMProvider" in content and "VertexAIProvider" not in content:
        print(f"Fixing {init_file}...")
        
        # Add direct import at the beginning
        new_content = content.replace(
            "from .mock import MockLLMProvider",
            "from .mock import MockLLMProvider\n\n# Directly import VertexAI provider\nfrom .vertex_ai import VertexAIProvider\n"
        )
        
        # Register the provider in the registry
        new_content = new_content.replace(
            "LLM_PROVIDERS: Dict[str, Type[LLMProvider]] = {\n    \"mock\": MockLLMProvider\n}",
            "LLM_PROVIDERS: Dict[str, Type[LLMProvider]] = {\n    \"mock\": MockLLMProvider,\n    \"vertex_ai\": VertexAIProvider\n}"
        )
        
        # Comment out the try/except import block to avoid warning
        start_idx = new_content.find("# Import VertexAI provider if available")
        end_idx = new_content.find("def create_llm_provider")
        
        if start_idx != -1 and end_idx != -1:
            try_block = new_content[start_idx:end_idx]
            commented_block = "# DISABLED DYNAMIC IMPORT:\n# " + try_block.replace("\n", "\n# ")
            new_content = new_content.replace(try_block, commented_block)
        
        # Write the modified content
        with open(init_file, "w") as f:
            f.write(new_content)
        
        print("Successfully fixed LLM provider imports!")
    else:
        print("No fix needed for LLM provider imports.")

if __name__ == "__main__":
    fix_llm_init()
EOF

chmod +x fix_imports.py

# Create a new Dockerfile that uses the fix script
cat > Dockerfile.patched << EOF
FROM python:3.10-slim-buster

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (for better layer caching)
COPY pyproject.toml poetry.lock ./

# Install Poetry 
RUN pip install --no-cache-dir poetry && \\
    pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir vertexai google-cloud-aiplatform google-genai

# Copy the rest of the application
COPY . .

# Install the application
RUN pip install -e .

# Make run.sh executable
RUN chmod +x run.sh

# Apply the import fix
COPY fix_imports.py /app/
RUN python /app/fix_imports.py

# Set environment variable for Google credentials
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/google-service-account.json
# Default to mock provider if no credentials
ENV USE_MOCK_PROVIDER=true

# Create an entrypoint script with provider selection logic
RUN echo '#!/bin/bash\\n\\
# check if USE_MOCK_PROVIDER is true or if credentials file does not exist\\n\\
if [ "\$USE_MOCK_PROVIDER" = "true" ] || [ ! -f "\$GOOGLE_APPLICATION_CREDENTIALS" ]; then\\n\\
    echo "Using mock LLM provider..."\\n\\
    # Update config files to use mock provider\\n\\
    sed -i '\\'s/# LLM Settings/# LLM Settings\\\\nLLM_PROVIDER = "mock"/\\'' /app/configs/financial_advisory.py\\n\\
    sed -i '\\'s/LLM_PROVIDER = "vertex_ai"/LLM_PROVIDER = "mock"/\\'' /app/configs/financial_advisory.py 2>/dev/null || true\\n\\
    exec python run_financial_advisory_mock.py "\$@"\\n\\
else\\n\\
    echo "Using Vertex AI provider with credentials at \$GOOGLE_APPLICATION_CREDENTIALS"\\n\\
    # Make sure config uses vertex_ai provider\\n\\
    if grep -q "LLM_PROVIDER" /app/configs/financial_advisory.py; then\\n\\
        sed -i '\\'s/LLM_PROVIDER = "mock"/LLM_PROVIDER = "vertex_ai"/\\'' /app/configs/financial_advisory.py\\n\\
    else\\n\\
        sed -i '\\'s/# LLM Settings/# LLM Settings\\\\nLLM_PROVIDER = "vertex_ai"/\\'' /app/configs/financial_advisory.py\\n\\
    fi\\n\\
    exec python run_financial_advisory.py "\$@"\\n\\
fi' > /app/docker-entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Set the command to run when the container starts
ENTRYPOINT ["/app/docker-entrypoint.sh"]
EOF

# Build the Docker image
docker build -t chat-factory-patched -f Dockerfile.patched .