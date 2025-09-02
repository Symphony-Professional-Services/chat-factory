# Datetime Distribution in Chat Factory

This document explains how to use the datetime distribution features in Chat Factory to control the temporal aspects of generated conversations.

## Overview

The datetime distribution system allows you to:

1. Generate conversations with realistic timestamps distributed over a specific time period
2. Control distribution patterns across days of the week, hours of the day, and months of the year
3. Generate realistic message timing patterns within conversations
4. Specify the exact number of conversations to generate within a time period

## Available Strategies

Chat Factory provides three built-in datetime distribution strategies:

### 1. Business Hours Strategy

Generates timestamps that follow typical business patterns:
- More conversations during weekdays (Mon-Fri) than weekends
- Concentrates conversations during business hours (9am-5pm by default)
- Allows customizing weekday weights and hour weights

```python
# Business hours configuration example
DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "business_hours"
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-03-31T23:59:59"
BUSINESS_HOURS_START = 9  # 9 AM
BUSINESS_HOURS_END = 17   # 5 PM
WEEKEND_WEIGHT = 0.2      # 20% of conversations on weekends
WEEKDAY_WEIGHTS = {
    'Monday': 0.25,
    'Tuesday': 0.2,
    'Wednesday': 0.2,
    'Thursday': 0.2,
    'Friday': 0.15
}
```

### 2. Uniform Distribution Strategy

Generates timestamps that are evenly distributed across the specified time period:
- Equal chance of selection for any date in the range
- Distributes conversations evenly by date
- Simplest option for testing or when specific patterns aren't needed

```python
# Uniform distribution configuration example
DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "uniform"
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-12-31T23:59:59"
```

### 3. Custom Period Strategy

Provides fine-grained control over time distributions:
- Specific date ranges with custom weighting
- Month-based weighting (e.g., more in Q1 than Q2)
- Special date support (e.g., holidays)
- Custom message timing patterns

```python
# Custom period configuration example
DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "custom_period"
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-12-31T23:59:59"

# Month weights (optional)
MONTH_WEIGHTS = {
    1: 1.5,   # January - 50% more conversations
    2: 1.5,   # February
    3: 1.5,   # March
    4: 1.0,   # April
    # ...other months
    12: 0.5   # December - 50% fewer conversations
}

# Special dates (optional)
SPECIAL_DATES = {
    '2024-01-01': 0.1,  # New Year's Day - 90% fewer conversations
    '2024-12-25': 0.1,  # Christmas Day - 90% fewer conversations
}

# Message timing patterns (optional)
MESSAGE_TIMING_PATTERNS = {
    'quick_exchange': {
        'mean_delay': 20,   # 20 seconds between messages
        'std_dev': 10,      # 10 seconds standard deviation
        'probability': 0.3  # 30% chance of this pattern
    },
    'normal_conversation': {
        'mean_delay': 60,   # 1 minute between messages
        'std_dev': 30,      # 30 seconds standard deviation
        'probability': 0.5  # 50% chance of this pattern
    },
    'thoughtful_discussion': {
        'mean_delay': 180,  # 3 minutes between messages
        'std_dev': 60,      # 1 minute standard deviation
        'probability': 0.2  # 20% chance of this pattern
    }
}
```

## Configuration Options

Here are all the available configuration options for datetime distribution:

| Option | Description | Default |
|--------|-------------|---------|
| `DATETIME_DISTRIBUTION_ENABLED` | Enable/disable datetime distribution | `False` |
| `DATETIME_STRATEGY` | Strategy type: "business_hours", "uniform", or "custom_period" | "business_hours" |
| `START_DATE` | Start of time period (ISO format) | Current date |
| `END_DATE` | End of time period (ISO format) | Current date + 30 days |
| `BUSINESS_HOURS_START` | Start of business hours (24-hour format) | 9 |
| `BUSINESS_HOURS_END` | End of business hours (24-hour format) | 17 |
| `WEEKEND_WEIGHT` | Proportion of conversations on weekends | 0.2 |
| `WEEKDAY_WEIGHTS` | Weights for each weekday (must sum to 1.0) | See example |
| `HOUR_WEIGHTS` | Weights for different times of day | See example |
| `MONTH_WEIGHTS` | Weights for different months of the year | Equal for all months |
| `SPECIAL_DATES` | Weights for specific dates | None |
| `MESSAGE_DELAY_MEAN` | Mean delay between messages (seconds) | 60 |
| `MESSAGE_DELAY_STD_DEV` | Standard deviation for delay (seconds) | 30 |
| `MESSAGE_TIMING_PATTERNS` | Patterns for message timing | See custom strategy example |

## Examples

### Generate 200 Conversations Over 3 Months with Business Hours Pattern

```python
# Configuration
DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "business_hours"
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-03-31T23:59:59"
NUM_CONVERSATIONS = 200

# Business hours settings
BUSINESS_HOURS_START = 8   # 8 AM
BUSINESS_HOURS_END = 18    # 6 PM
WEEKEND_WEIGHT = 0.1       # 10% of conversations on weekends

# Focus more conversations on Monday and Tuesday
WEEKDAY_WEIGHTS = {
    'Monday': 0.3,
    'Tuesday': 0.25,
    'Wednesday': 0.2,
    'Thursday': 0.15,
    'Friday': 0.1
}
```

### Generate Conversations Over a Year with Seasonal Patterns

```python
# Configuration
DATETIME_DISTRIBUTION_ENABLED = True
DATETIME_STRATEGY = "custom_period"
START_DATE = "2024-01-01T00:00:00"
END_DATE = "2024-12-31T23:59:59"
NUM_CONVERSATIONS = 500

# Month weights for seasonal patterns
MONTH_WEIGHTS = {
    1: 1.2,   # Winter - higher activity
    2: 1.2,
    3: 1.0,   # Spring
    4: 1.0,
    5: 1.0,
    6: 0.8,   # Summer - lower activity
    7: 0.7,
    8: 0.7,
    9: 1.0,   # Fall
    10: 1.0,
    11: 1.2,   # Early winter
    12: 1.2
}
```

## Integration with Other Strategies

The datetime distribution system is designed to work alongside the existing taxonomy and generation strategies. It adds temporal dimension to conversations without affecting the content generation process.

You can enable datetime distribution for any use case by adding the appropriate configuration settings, such as in this example for the financial advisory use case with Gemini 2.0.