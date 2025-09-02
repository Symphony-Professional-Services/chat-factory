# Scripts Directory README

This directory contains various utility scripts for building, testing, and processing data for the `chat-factory` project.

---

### `build_and_test_docker.sh`

**What it does:**
This script automates the process of building the `chat-factory` Docker container and running a series of tests against it. It tests the container in two modes:

1.  **Mock Provider Mode:** Runs the container using the mock LLM provider, which doesn't require any external credentials.
2.  **VertexAI Provider Mode:** Runs the container using the real Vertex AI provider, which requires a valid `service-account-key.json` file.

**When to use it:**
Use this script to quickly verify that the Docker setup is working correctly and that the application can run in both mock and real environments.

**How to use it:**

```bash
./scripts/build_and_test_docker.sh
```

**Note:** For the VertexAI test to run, you must have a `service-account-key.json` file in the root of the project directory.

---

### `create_validation_set.py`

**What it does:**
This script reads the raw synthetic chat data (in JSON format) and transforms it into a single CSV file. This CSV file is structured to be used as a validation set for evaluating classification models.

**When to use it:**
Use this script when you need to prepare the generated data for model training or evaluation. It is particularly useful for creating a ground truth dataset for classification tasks.

**How to use it:**

```bash
python scripts/create_validation_set.py --source <path_to_generated_data> --output <path_to_output_csv>
```

**Example:**

```bash
python scripts/create_validation_set.py --source synthetic_data/run_20250319_033137/ --output evaluation_data/validation_set.csv
```

---


### `validate_data.py`

**What it does:**
This script performs a series of validation checks on the generated synthetic data. It checks for data completeness, schema compliance, temporal distribution, and other data quality metrics.

**When to use it:**
Use this script to assess the quality of the generated data. It is recommended to run this script after each generation run to ensure that the data meets the required quality standards.

**How to use it:**

```bash
python scripts/validate_data.py --data-dir <path_to_generated_data> --generator-log <path_to_generator_log>
```

**Example:**

```bash
python scripts/validate_data.py --data-dir synthetic_data/run_20250319_033137/ --generator-log output/logs/synthetic_chat_generator.log
```

---

### `format_data.py`

**What it does:**
This script processes the generated multi-conversation JSON files and formats them into individual JSON files for each conversation. It also restructures the data, removing timestamps from individual messages and adding a formatted date to the metadata.

**When to use it:**
Use this script when you need to break down the generated data into a more granular format, with each conversation in its own file.

**How to use it:**

```bash
python scripts/format_data.py --source <path_to_generated_data> --target <path_to_processed_data>
```

**Example:**

```bash
python scripts/format_data.py --source synthetic_data/run_20250319_033137/ --target processed_synthetic_data/run_20250319_033137/
```

---

### `install.sh`

**What it does:**
This script automates the setup of the local development environment. It checks if `poetry` is installed, installs the project dependencies, creates the necessary directories, and makes the run scripts executable.

**When to use it:**
Use this script when you are setting up the project for the first time on a new machine.

**How to use it:**

```bash
./scripts/install.sh
```

---

### `post_processing_add_company_entities.py`

**What it does:**
This script merges company entity information from the conversation manifests into the generated synthetic data. It reads the manifest logs to find the key companies that were targeted for each conversation and adds this information to the corresponding conversation JSON file.

**When to use it:**
Use this script when you need to enrich the generated data with the ground truth company entities. This is particularly useful for training and evaluating named entity recognition (NER) models.

**How to use it:**

```bash
python scripts/post_processing_add_company_entities.py --run_id <run_id>
```

**Example:**

```bash
python scripts/post_processing_add_company_entities.py --run_id run_20250319_033137
```

---

### `run_tests.py`

**What it does:**
This is a custom test runner script that discovers and runs all the unit tests in the `tests/` directory.

**When to use it:**
Use this script to run the project's unit tests. It is recommended to run the tests after making any changes to the code to ensure that everything is still working as expected.

**How to use it:**

```bash
python scripts/run_tests.py
```

---

### `test_company_regex.py`

**What it does:**
This script tests the regular expression patterns used for detecting company names and tickers in text. It is a debugging tool for issues related to company mention detection.

**When to use it:**
Use this script when you are developing or debugging the company mention detection logic. It can help you to verify that the regex patterns are working as expected.

**How to use it:**

```bash
python scripts/test_company_regex.py
```

---
