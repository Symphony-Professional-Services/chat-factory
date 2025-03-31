### RUN VALIDATION TESTS ON OUTPUT DATA

### How to run

```bash
python validate_data.py     --data-dir synthetic_data/financial_advisory_3_30_25_130k     --generator-log output/logs/financial_advisory_3_30_25_130k.log     --report-dir validation_reports     --config validation_reports/financial_advisory_tests.yaml     --generator-config configs/financial_advisory_gemini2.py # Optional
```