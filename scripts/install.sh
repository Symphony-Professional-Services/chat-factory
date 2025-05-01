#!/bin/bash

# Installation script for Chat Factory

echo "Installing Chat Factory..."

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Installing poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "Installing dependencies with poetry..."
poetry install

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p synthetic_data
mkdir -p few_shot_examples
mkdir -p conversation_scripts
mkdir -p output/logs
mkdir -p taxonomies

# Copy taxonomy file if it doesn't exist in taxonomies directory
if [ ! -f taxonomies/financial_advisory.json ] && [ -f taxonomy.json ]; then
    echo "Copying taxonomy.json to taxonomies/financial_advisory.json..."
    cp taxonomy.json taxonomies/financial_advisory.json
fi

# Make run scripts executable
echo "Making run scripts executable..."
chmod +x run.sh
chmod +x run_financial_advisory.py

echo "Installation complete!"
echo "Run './run.sh' to generate conversations using the default config."
echo "Run './run_financial_advisory.py --num 10' to generate 10 financial advisory conversations."