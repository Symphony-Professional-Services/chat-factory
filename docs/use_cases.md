# Chat Factory Use Cases

This document describes the different use cases available in the chat-factory project and how to use them with Docker.

## Available Use Cases

### 1. Financial Advisory

Generates conversations between financial advisors and their clients.

**Configuration:**
- Config File: `configs/financial_advisory.py`
- Run Script: `run_financial_advisory.py`
- Taxonomy File: `taxonomies/financial_advisory.json`

**Docker Usage:**
```bash
docker run --rm -e USE_CASE=financial_advisory -e USE_MOCK_PROVIDER=false \
  -v /path/to/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "financial_run" --num 10
```

### 2. Company Tagging

Generates conversations that include specific company mentions.

**Configuration:**
- Config File: `configs/company_tagging.py`
- Run Script: `run_company_tagging.py`
- Taxonomy File: `taxonomies/company_tagging.json`
- Company Data: `company_data_gemini2.csv`

**Docker Usage:**
```bash
docker run --rm -e USE_CASE=company_tagging -e USE_MOCK_PROVIDER=false \
  -v /path/to/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "company_run" --num 10
```

### 3. Voice of the Customer (VOC)

Generates "Voice of the Customer" conversations for the insurance industry.

**Configuration:**
- Config File: `configs/voc_gemini2.py`
- Run Script: `run_voc.py`
- Taxonomy File: `taxonomies/voc.json`

**Docker Usage:**
```bash
docker run --rm -e USE_CASE=voc -e USE_MOCK_PROVIDER=false \
  -v /path/to/service-account-key.json:/app/google-service-account.json \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/synthetic_data:/app/synthetic_data \
  chat-factory:latest --run_id "voc_run" --num 10
```

## Creating a New Use Case

To create a new use case:

1. **Create a config file**:
   - Add a new config file in the `configs/` directory (e.g., `configs/new_use_case.py`)

2. **Create a taxonomy file**:
   - Add a new taxonomy file in the `taxonomies/` directory (e.g., `taxonomies/new_use_case.json`)

3. **Create a run script**:
   - Create a run script (e.g., `run_new_use_case.py`)

4. **Build a new Docker image**:
   ```bash
   docker build -t chat-factory:latest .
   ```

5. **Run the new use case**:
   ```bash
   docker run --rm -e USE_CASE=new_use_case -e USE_MOCK_PROVIDER=true \
     -v $(pwd)/output:/app/output \
     -v $(pwd)/synthetic_data:/app/synthetic_data \
     chat-factory:latest --run_id "new_use_case_run" --num 10
   ```

## Command-line Arguments

All run scripts accept these common arguments:

- `--run_id`: Unique identifier for this generation run (used in output filenames)
- `--num`: Number of conversations to generate

Specific use cases may support additional arguments.
