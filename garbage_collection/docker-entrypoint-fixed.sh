#!/bin/bash

# Function to check if Vertex AI packages are available to Poetry
check_vertex_packages() {
    echo "Checking for Vertex AI packages..."
    
    # Verify that packages can be imported
    poetry run python -c "
try:
    import vertexai
    import google.cloud.aiplatform
    import google.genai
    print('✅ All required packages are available')
    exit(0)
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"
    return $?
}

# Function to install packages if they're missing
ensure_packages_installed() {
    echo "Installing required packages in Poetry environment..."
    
    # Install packages in Poetry environment
    poetry run pip install --upgrade vertexai google-cloud-aiplatform google-genai
    
    # Verify installation was successful
    check_vertex_packages
    return $?
}

# Check if we should use mock provider
if [ "$USE_MOCK_PROVIDER" = "true" ] || [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Using mock LLM provider..."
    
    # Update config files to use mock provider
    sed -i 's/# LLM Settings/# LLM Settings\nLLM_PROVIDER = "mock"/' /app/configs/financial_advisory.py
    sed -i 's/LLM_PROVIDER = "vertex_ai"/LLM_PROVIDER = "mock"/' /app/configs/financial_advisory.py 2>/dev/null || true
    
    exec poetry run python run_financial_advisory_mock.py "$@"
else
    echo "Using Vertex AI provider with credentials at $GOOGLE_APPLICATION_CREDENTIALS"
    
    # Make sure config uses vertex_ai provider
    if grep -q "LLM_PROVIDER" /app/configs/financial_advisory.py; then
        sed -i 's/LLM_PROVIDER = "mock"/LLM_PROVIDER = "vertex_ai"/' /app/configs/financial_advisory.py
    else
        sed -i 's/# LLM Settings/# LLM Settings\nLLM_PROVIDER = "vertex_ai"/' /app/configs/financial_advisory.py
    fi
    
    # Check if packages can be imported inside the Poetry environment
    check_vertex_packages
    if [ $? -ne 0 ]; then
        # Install packages in Poetry environment if they're not available
        echo "Packages not available in Poetry environment, installing..."
        ensure_packages_installed
        
        if [ $? -ne 0 ]; then
            echo "Failed to install packages in Poetry environment. Falling back to mock provider."
            sed -i 's/LLM_PROVIDER = "vertex_ai"/LLM_PROVIDER = "mock"/' /app/configs/financial_advisory.py
            exec poetry run python run_financial_advisory_mock.py "$@"
        fi
    fi
    
    # All checks passed, run with Vertex AI
    echo "Running with Vertex AI provider..."
    exec /app/run.sh "$@"
fi