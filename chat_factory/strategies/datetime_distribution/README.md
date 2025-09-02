# Datetime Distribution Strategies README

This directory contains the strategy implementations for controlling the temporal distribution of the generated conversations. This is a core strategy component that allows for the creation of more realistic and contextually appropriate synthetic data.

## Overview

The purpose of the datetime distribution strategies is to generate timestamps for both the conversations themselves and the individual messages within them. By simulating different temporal patterns, we can create data that more accurately reflects real-world communication patterns.

For example, we can generate conversations that are more likely to occur during business hours on weekdays, or we can simulate a flurry of messages in a short period of time, followed by a long pause.

## Core Concepts

The datetime distribution strategies are based on the `DatetimeStrategy` abstract base class, which defines the common interface for all datetime strategies. The `SyntheticChatGenerator` uses a datetime strategy to:

1.  **Generate a timestamp for each conversation:** This determines the date and time when the conversation is supposed to have taken place. **Note:** This timestamp represents the **start** of the conversation.
2.  **Generate timestamps for each message:** This determines the time when each message within a conversation was sent. The timestamp of the first message will be the same as the conversation timestamp, and subsequent messages will have timestamps that are incrementally later, simulating realistic delays and response times.

## Available Strategies

### `business_hours_strategy.py`

*   **Purpose:** This strategy generates timestamps that are weighted towards business hours and workdays.
*   **How it works:**
    *   It is more likely to generate timestamps on weekdays (Monday-Friday) than on weekends.
    *   Within a given day, it is more likely to generate timestamps during business hours (e.g., 9am-5pm).
    *   It simulates realistic delays between messages, with shorter delays for quick exchanges and longer delays for more thoughtful responses.

### `custom_period_strategy.py`

*   **Purpose:** This strategy provides fine-grained control over the time distribution, allowing for the simulation of specific periods and patterns.
*   **How it works:**
    *   It can be configured with custom weights for different hours of the day, days of the week, and months of the year.
    *   It supports the definition of special dates (e.g., holidays) with their own weights.
    *   It allows for the configuration of different message timing patterns (e.g., `quick_exchange`, `thoughtful_discussion`) with different delay characteristics.

### `uniform_distribution_strategy.py`

*   **Purpose:** This strategy generates timestamps that are uniformly distributed across a given time period.
*   **How it works:**
    *   It randomly selects a date and time within the configured date range, with each point in time having an equal probability of being chosen.
    *   This strategy is useful for testing or when no specific time distribution is needed.

## How to Use

To use a datetime distribution strategy, you need to enable it in your use-case-specific configuration file and specify the strategy you want to use.

```python
# configs/my_new_use_case.py

DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "business_hours"  # or "custom_period", "uniform"

# Optional: Configure the parameters for the chosen strategy
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-12-31T23:59:59"
BUSINESS_HOURS_START = 8
BUSINESS_HOURS_END = 18
```

## How to Add a New Datetime Strategy

1.  **Create a new strategy class:** Create a new Python file in this directory and define a new class that inherits from `DatetimeStrategy`.

2.  **Implement the required methods:** Implement the `generate_conversation_timestamp` and `generate_message_timestamps` methods with your custom logic.

3.  **Register the new strategy:** In `factory.py` in this directory, import your new strategy class and add it to the `if/elif/else` block in the `create_datetime_strategy` function.