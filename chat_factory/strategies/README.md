# Chat Factory Strategy Pattern

This document outlines the strategy pattern used in Chat Factory for generating synthetic conversations. It explains each component's role, their interactions, and how to implement new features like datetime distributions and message count controls.

## Architecture Overview

The Chat Factory uses a strategy pattern to separate different concerns in the conversation generation process. The main components and their relationships are outlined below:

```
┌───────────────────────┐
│ SyntheticChatGenerator│
└───────────┬───────────┘
            │ orchestrates
            ▼
┌───────────────────────────────────────────────────────────┐
│                 Strategy Components                        │
├─────────────────┬─────────────────┬─────────────────┬─────┘
│                 │                 │                 │
▼                 ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Taxonomy    │  │ Generation  │  │ Few-Shot    │  │ LLM         │
│ Strategy    │  │ Strategy    │  │ Strategy    │  │ Provider    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
   │                │                │
   │                │                │
   ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Taxonomy    │  │ Conversation│  │ Example     │
│ Selection   │  │ Construction│  │ Retrieval   │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Key Components and Responsibilities

### 1. Strategy Base Classes 

Located in `strategies/base/`:

- **`TaxonomyStrategy`**: Manages loading and selecting topics from taxonomy files
- **`GenerationStrategy`**: Handles conversation structure, prompt construction, and LLM response processing
- **`FewShotStrategy`**: Manages example retrieval for few-shot learning

### 2. Implementation Strategies

Located in domain-specific folders (e.g., `financial_advisory/`, `company_tagging/`):

- Each use case implements specialized versions of the base strategies
- These implementations contain domain-specific logic for conversation generation

### 3. Generator

The `SyntheticChatGenerator` in `generator.py` orchestrates the entire process:

1. Takes strategy objects via dependency injection
2. Manages conversation lifecycle from topic selection to saving
3. Coordinates between different strategies during generation

## Data Flow in Conversation Generation

1. **Topic Selection**:
   - `TaxonomyStrategy` loads taxonomy from JSON file
   - Flattens the hierarchical taxonomy into (category, topic, subtopic) tuples
   - Selects topics based on weighting or random distribution

2. **Conversation Blueprint Creation**:
   - `GenerationStrategy` creates a blueprint with conversation parameters
   - Defines message characteristics, style, and content requirements
   - May include specialized parameters (e.g., company mentions)

3. **Few-Shot Example Selection**:
   - `FewShotStrategy` retrieves relevant examples based on topic and conversation type
   - Formats examples for inclusion in LLM prompts

4. **Prompt Construction**:
   - `GenerationStrategy` combines topic, blueprint, and examples into a prompt
   - Formats prompt according to LLM provider requirements

5. **LLM Generation**:
   - `LLMProvider` sends prompt to LLM and receives response
   - `GenerationStrategy` processes response into standardized format

6. **Conversation Saving**:
   - Generator creates conversation objects with metadata
   - Groups conversations by advisor-client pairs
   - Saves to JSON files in the output directory

## Current Datetime and Message Distribution Implementation

Currently, the temporal aspects are handled in a limited way:

- **Conversation Timestamps**: Set at creation time using `datetime.now().isoformat()`
- **Message Timing**: Messages don't have individual timestamps, only an ordering
- **Message Distribution**: Controlled by message length ratios in generation strategies
- **Conversation Grouping**: Multiple conversations between same participants are grouped in single files

## Adding Datetime Distribution Controls

To implement datetime distribution and message count controls:

### 1. Create a New Strategy Class

Create a `DatetimeStrategy` base class in `strategies/base/datetime_strategy.py`:

```python
class DatetimeStrategy(ABC):
    """Strategy for controlling temporal aspects of conversations."""
    
    @abstractmethod
    def generate_conversation_timestamp(self, conversation_number: int) -> str:
        """Generate a timestamp for a conversation."""
        pass
        
    @abstractmethod
    def generate_message_timestamps(self, 
                                   conversation_timestamp: str,
                                   num_messages: int) -> List[str]:
        """Generate timestamps for each message in a conversation."""
        pass
        
    @abstractmethod
    def get_message_count_distribution(self, 
                                      time_period: Tuple[str, str], 
                                      total_conversations: int) -> Dict[str, int]:
        """Get distribution of messages across a time period."""
        pass
```

### 2. Extend Model Classes

Update `models/conversation.py` to include timestamps for individual messages:

```python
@dataclass
class ChatLine:
    speaker: str  # "0" = client, "1" = advisor
    text: str
    timestamp: Optional[str] = None  # Add timestamp field
```

### 3. Modify Generator Class

Update `SyntheticChatGenerator` to use the new strategy:

- Add `datetime_strategy` parameter to constructor
- Update `process_conversation` to assign timestamps to messages
- Modify `generate_synthetic_data` to use time-based distributions

### 4. Implement Specialized Strategies

Create implementations like:

- `BusinessHoursDatetimeStrategy`: Focus on business hours distribution
- `WeekdayWeightedStrategy`: Weight conversations toward business days
- `CustomPeriodStrategy`: Allow specific start/end dates with distribution

## Example Implementation for Time-Distributed Messages

```python
class BusinessHoursDatetimeStrategy(DatetimeStrategy):
    def __init__(self, config):
        self.config = config
        self.start_date = config.START_DATE
        self.end_date = config.END_DATE
        
    def generate_conversation_timestamp(self, conversation_number: int) -> str:
        # Generate timestamp within business hours
        # Weight toward middle of day and weekdays
        # ...
        
    def generate_message_timestamps(self, conversation_timestamp: str, num_messages: int) -> List[str]:
        # Generate realistic gaps between messages
        # Account for thinking/typing time
        # ...
```

## Integration Path

1. Create the datetime strategy classes
2. Update model classes to support message timestamps
3. Modify generator to use the new strategies
4. Update implementations in domain-specific folders
5. Add configuration options for datetime controls

This modular approach allows you to implement advanced temporal controls while maintaining the clean architecture of the existing strategy pattern.