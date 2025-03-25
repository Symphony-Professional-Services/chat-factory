# Company Mention Integration Guide

This guide explains how to implement and maintain company mention functionality in the Chat Factory system.

## Overview

The company mention system allows specific companies to be featured in financial advisory conversations. This is implemented with:

1. **Configurable targeting probability** - Control what percentage of conversations include companies
2. **Distribution control** - Configure how many companies appear in a conversation (1, 2, or 3+)
3. **Detection and metrics** - Track which companies actually appear in generated conversations
4. **Regex-based validation** - Ensure accurate detection, especially for short ticker symbols

## Configuration

The company targeting system is configured in the use case configuration file. For example, in `configs/financial_advisory_gemini2.py`:

```python
COMPANY_TARGETING = {
    "enabled": True,          # Set to True to enable company targeting
    "probability": 0.3,       # 30% of conversations will include company mentions
    "min_companies": 1,       # Minimum companies to include in a conversation
    "max_companies": 3,       # Maximum companies to include in a conversation
    "decision_model": "topic_based"  # Future extension point for smarter company selection
}
```

## Company Data Format

Companies are loaded from a CSV file or a fallback list in the strategy implementation. Each company has the following attributes:

- **name**: Primary company name (e.g., "Apple")
- **ticker**: Stock ticker symbol (e.g., "AAPL")
- **industry**: Company's industry sector (e.g., "Technology")
- **variations**: Alternative names, separated by semicolons (e.g., "Apple Inc;APPL")
- **formal_name**: Official company name (e.g., "Apple Inc.")

## Implementation Details

### 1. Company Selection

In the `create_manifest_blueprint` method of `FinancialAdvisoryGenerationStrategy`:

- Random value determines if company targeting is enabled for a conversation
- If enabled, a weighted random selection determines how many companies (1, 2, or 3)
- Selected companies are included in the blueprint for the conversation

### 2. Prompt Generation

When constructing the LLM prompt:
- If company targeting is enabled, instructions are added to include those companies
- Companies are displayed with their variations
- LLM is instructed to mention each company at least once

### 3. Company Detection

After generation, the `check_company_mentions` function analyzes the text:
- Uses regex patterns with word boundaries to detect company names
- Employs special patterns for short ticker symbols (1-2 chars) to avoid false positives
- Counts mentions of each company and tracks which companies were found

### 4. Metrics Calculation

At the end of a run, metrics are calculated:
- Percentage of conversations with company targeting enabled
- Success rate (how many targeted conversations actually included companies)
- Distribution of company counts (70/20/10 target for 1/2/3+ companies)
- Most frequently mentioned companies

## Special Considerations

### Short Ticker Symbols (1-2 characters)

Tickers like "V" (Visa) or "MA" (Mastercard) require special handling to avoid false positives:

1. Only count when they appear with specific context, such as:
   - With dollar sign: $V
   - As ticker: ticker: V
   - With context: V stock, V shares, position in V

2. The regex patterns for detecting these include:
   - `[$]V\b`
   - `\bV[ ]?[(]`
   - `ticker:?\s+V\b`
   - `\bV[ ]stock`
   - `\bV[ ]shares`

## Testing

The system includes comprehensive tests:
- `test_company_metrics.py` - Tests metrics calculation and aggregation
- `test_company_selection.py` - Tests company selection and prompt integration
- `test_company_regex.py` - Script to test regex patterns for company detection

## Troubleshooting

Common issues and solutions:

1. **Companies not showing in metrics**
   - Check if probability is set too low
   - Verify log_conversation_manifest is correctly tracking detected companies

2. **Too many company mentions**
   - Check if LLM is ignoring conversation directives
   - Review prompt template for clarity in instructions

3. **False positives with short ticker symbols**
   - Refine regex patterns in check_company_mentions
   - Add more context requirements for short symbols

4. **False negatives (missing companies)**
   - Ensure all variations are included in company data
   - Check that word boundary regex (`\b`) isn't cutting off company names

## Example Run Output

A successful run should show metrics like:

```
===== COMPANY TARGETING METRICS =====
Company targeting configuration: probability=0.30, min_companies=1, max_companies=3
Conversations with company targeting enabled: 6 (30.0% of all conversations)
Expected conversations with company targeting: 6 (30.0% of all conversations)
Conversations with at least one company mentioned: 6 (100.0% success rate, 30.0% of all conversations)

----- Company Count Distribution -----
1_company: 4 conversations (66.7%) █████████████
2_companies: 1 conversations (16.7%) ███
3+_companies: 1 conversations (16.7%) ███

Average company mentions per conversation (when present): 2.50

----- Company Mentions Distribution -----
1 mentions: 1 conversations (16.7%) ███
2 mentions: 3 conversations (50.0%) █████████
3 mentions: 1 conversations (16.7%) ███
4 mentions: 1 conversations (16.7%) ███

----- Top 10 Company Mentions -----
Microsoft: 5 mentions (33.3%) ██████
Apple: 4 mentions (26.7%) █████
Johnson & Johnson: 2 mentions (13.3%) ██
Visa: 2 mentions (13.3%) ██
Verizon: 1 mentions (6.7%) █
BlackRock: 1 mentions (6.7%) █
```