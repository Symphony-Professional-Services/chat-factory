# Few-Shot Example Strategies README

This directory contains the strategy implementations for selecting and formatting few-shot examples that are used to guide the LLM in the conversation generation process.

## Overview

Few-shot examples are a powerful technique for showing the LLM the desired style, tone, and format of the generated conversations. By providing a few high-quality examples in the prompt, we can significantly improve the quality and consistency of the generated output.

The few-shot example strategies are responsible for selecting the most relevant examples for a given conversation and formatting them for inclusion in the prompt.

## `BasicFewShotStrategy`

This is the default implementation of the few-shot example strategy. It is designed to be simple and effective, with a fallback mechanism to ensure that some examples are always found.

### How it Works

The `BasicFewShotStrategy` attempts to find relevant examples by searching for files in the `few_shot_examples/` directory in the following order of specificity:

1.  **Exact Match:** It first looks for an example file that exactly matches the category, topic, and subtopic of the conversation to be generated.
2.  **Topic Match:** If no exact match is found, it looks for an example file that matches the category and topic.
3.  **Category Match:** If still no match is found, it looks for an example file that matches only the category.
4.  **Conversation Type Match:** As a further fallback, it looks for an example file that matches the conversation type.
5.  **Generic Examples:** Finally, if no other examples are found, it falls back to using the `generic.txt` example file.

This fallback mechanism ensures that the LLM always has at least one example to learn from, even if there are no specific examples for the current topic.

### How to Add New Few-Shot Examples

To add new few-shot examples, simply create a new `.txt` file in the `few_shot_examples/` directory. The name of the file should correspond to the category, topic, or conversation type that the examples are for. For example, an example for the "Market Commentary" category should be named `Market Commentary.txt`.

### How to Add a New Few-Shot Strategy

If you need more advanced logic for selecting few-shot examples (e.g., based on semantic similarity), you can create a new few-shot strategy:

1.  **Create a new strategy class:** Create a new Python file in this directory and define a new class that inherits from `FewShotExampleStrategy`.

2.  **Implement the required methods:** Implement the `get_examples` and `format_examples` methods with your custom logic.

3.  **Register the new strategy:** In `chat_factory/strategies/__init__.py`, import your new strategy class and add it to the `FEW_SHOT_STRATEGIES` dictionary.

4.  **Update the configuration:** In your use-case-specific configuration file, set the `FEW_SHOT_STRATEGY` variable to the name of your new strategy.
