# Company Tagging Functionality

This document explains how to use the company tagging functionality in the Chat Factory framework.

## Overview

The company tagging functionality allows for the generation of synthetic conversations that include realistic mentions of companies. This is useful for:

- Training entity recognition models to identify company mentions
- Creating test data with different variations of company names
- Simulating financial conversations about specific companies

## Features

- **Company Name Variations**: Supports multiple variations of company names (full names, abbreviations, etc.)
- **Misspellings**: Can include common misspellings to make data more realistic
- **Ticker Symbols**: Incorporates stock ticker symbols in the conversations
- **Configurable Density**: Control how many companies appear in each conversation
- **Taxonomy-Driven**: Different conversation types can have different company mention patterns

## Getting Started

### Prerequisites

1. A CSV file with company data in the following format:
   ```
   name,ticker,sector,variations,misspellings,formal_name,other_metadata
   Apple,AAPL,Technology,"Apple Inc;APPL","Aple;Appel","Apple Inc.","Founded by Steve Jobs"
   ```

2. A company tagging taxonomy file (see `taxonomies/company_tagging.json`)

### Running Company Tagging Generation

To generate conversations with company tagging:

```bash
python run_company_tagging.py --config configs.company_tagging
```

For testing without requiring a real LLM API:

```bash
python run_company_tagging.py --config configs.company_tagging --use_mock
```

### Configuration Options

Key configuration settings in `configs/company_tagging.py`:

- `NUM_CONVERSATIONS`: Number of conversations to generate
- `COMPANY_DATA_FILE`: Path to the CSV file with company data
- `TAXONOMY_FILE`: Path to the taxonomy file with conversation types
- `COMPANY_TARGETING`: Settings for company mentions

## Architecture

The company tagging functionality is implemented using the strategy pattern:

- `CompanyTaggingTaxonomyStrategy`: Handles the taxonomy with conversation types
- `CompanyTaggingGenerationStrategy`: Manages the generation of company mentions

## Conversation Types

The taxonomy file defines conversation types with company tagging settings:

```json
"conversation_types": {
  "Trade discussions": {
    "description": "Conversations focused on trades",
    "company_tagging": {
      "enabled": true,
      "company_count_options": [2, 3, 4],
      "probability": 1.0,
      "min_companies": 2,
      "max_companies": 4
    }
  }
}
```

Each conversation type can have custom settings for:
- Whether company tagging is enabled
- How many companies to include
- Probability of including companies

## Example Output

Generated conversations will include company mentions in the conversation text and also track all mentioned companies in the `company_mentions` field:

```json
{
  "conversation_id": "run_id_123",
  "timestamp": "2025-03-22T14:22:33.228465",
  "category": "Company News",
  "topic": "Strategic Initiatives",
  "lines": [
    {
      "speaker": "1",
      "text": "Let's discuss the recent earnings report from Apple. They've shown impressive growth this quarter."
    },
    {
      "speaker": "0",
      "text": "I've been following AAPL closely. What specific numbers stood out to you?"
    }
  ],
  "company_mentions": [
    "Apple",
    "AAPL",
    "Microsoft"
  ]
}
```

## Processing and Analysis

The conversation manifests (stored in the manifest log) contain information about which companies were targeted for each conversation. This allows for:

- Evaluating company mention frequency
- Analyzing distribution of company references
- Tracking variations and misspellings