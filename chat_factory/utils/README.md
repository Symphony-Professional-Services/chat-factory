# Utils Directory README

This directory contains various helper functions and utilities that are used throughout the `chat-factory` application.

## Overview

The `utils` package is a collection of modules that provide common, reusable functionality. This helps to keep the main application logic clean and focused on the core task of conversation generation.

## Components

### `batch_logging.py`

This file contains the `SummaryStatisticsLogger` class, which is used to log detailed metrics about the conversation generation process. It calculates and logs information about:

*   Temporal distribution (by day, week, and month)
*   Advisor-client distribution and interactions
*   Company mention metrics

### `__init__.py`

This file contains several utility functions:

*   **`sanitize_filename()`:** Removes or replaces characters that are invalid in filenames.
*   **`setup_logging()`:** Sets up the logging for the application, including file and console handlers.
*   **`ensure_directory()`:** Ensures that a directory exists, creating it if necessary.

## How to Add New Utilities

To add a new utility function, you should:

1.  **Determine the appropriate module:** Decide which module the new function belongs to. If it is a general-purpose function, you can add it to the `__init__.py` file. If it is related to a specific functionality (e.g., file operations), you can create a new module (e.g., `file_utils.py`).

2.  **Add the function:** Add the new function to the chosen module. Ensure that the function is well-documented with a clear docstring that explains its purpose, arguments, and return value.

3.  **Add unit tests:** Add unit tests for the new function in the `tests/` directory to ensure that it is working correctly.
