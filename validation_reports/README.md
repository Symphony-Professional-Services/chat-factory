# Validation Reports README

This directory contains the necessary files for running validation tests on the generated synthetic data, as well as the output reports from those tests.

## Overview

The validation process is designed to ensure the quality and integrity of the generated data. It runs a suite of tests to check for completeness, schema compliance, data distribution, and other important metrics.

## How to Run Validation Tests

To run the validation tests, you can use the `validate_data.py` script from the `scripts/` directory. The script requires several arguments to specify the data to be validated, the generator log file, and the validation configuration.

```bash
python scripts/validate_data.py \
    --data-dir <path_to_generated_data> \
    --generator-log <path_to_generator_log> \
    --report-dir validation_reports \
    --config <path_to_validation_config> \
    --generator-config <path_to_generator_config> # Optional
```

**Example:**

```bash
python scripts/validate_data.py \
    --data-dir synthetic_data/financial_advisory_3_30_25_130k \
    --generator-log output/logs/financial_advisory_3_30_25_130k.log \
    --report-dir validation_reports \
    --config validation_reports/financial_advisory_tests.yaml \
    --generator-config configs/financial_advisory_gemini2.py
```

## Configuration

The validation tests are configured using a YAML file (e.g., `financial_advisory_tests.yaml`). This file allows you to enable or disable specific tests and set the thresholds for passing or failing a test.

### `tests_enabled`

This section allows you to enable or disable specific tests.

```yaml
tests_enabled:
  completeness: true
  schema: true
  temporal: true
  distributions: true
  company_mentions: true
  conversation_stats: true
  deduplication: true # Set to false to skip this slow test
```

### Thresholds & Parameters

This section allows you to override the default thresholds for the validation tests.

```yaml
completeness_tolerance_percent: 0.5
min_company_mention_success_rate: 0.75
dedup_similarity_threshold: 0.97
min_topic_coverage_percent: 95.0
```

## Interpreting the Validation Report

The validation script generates a detailed report in a text file (e.g., `validation_report_financial_advisory_3_30_25_130k.txt`). The report provides a summary of the test results, including the status of each test (PASS, WARN, or FAIL) and detailed metrics.

### Test Statuses

*   **PASS:** The test passed successfully.
*   **WARN:** The test passed, but with some warnings that you should be aware of.
*   **FAIL:** The test failed, indicating a potential issue with the generated data.
*   **ERROR:** The test could not be run due to an error (e.g., a missing file).
*   **SKIP:** The test was skipped because it was disabled in the configuration.

### Example Report

```
============================================================
Data Validation Report
Generated: 2025-03-31 13:12:35
============================================================

Test:    Completeness Check (Manifest Count)
Status:  WARN
Message: WARN: Found 129998 manifest entries, slightly below target 130000. Found gaps in conv_index: 2 missing up to max index 130000.
...
----------------------------------------
Test:    Deduplication Check
Status:  PASS
Message: PASS: No near-duplicate conversations found (threshold=0.97) among 596 checked documents (full dataset sample).
...
============================================================
Status Summary:
- WARN: 3
- PASS: 4

Overall Validation Status: WARN
============================================================
```

By reviewing the validation report, you can quickly assess the quality of the generated data and identify any potential issues that need to be addressed.
