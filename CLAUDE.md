# Chat Factory Helper Guide

## Build Commands
- Install dependencies: `poetry install`
- Run the application: `poetry run python main.py --run_id "run_id" --config configs/config_name.py`
- Run metrics: `poetry run python metrics.py --run_id "run_id" --metadata "metadata"`
- Run with shell script: `./run.sh` (creates directories and handles logging)

## Test-Driven Development Workflow
1. **Write Test First**: Create test cases before writing implementation code
   - `poetry run python -m unittest tests/test_module.py`
   - `poetry run python -m unittest tests.test_module.TestClass.test_method`

2. **Test Cases Guidelines**:
   - Test function behavior with various inputs
   - Test edge cases and error conditions
   - Mock external dependencies (API calls, file I/O)
   - For data transformations, verify input/output formats
   - For async code, use `IsolatedAsyncioTestCase`

3. **Component Test Focus Areas**:
   - **Data Processing**: Input validation, transformation, storage formats
   - **API Interactions**: Request formatting, error handling, response parsing
   - **Taxonomy Handling**: Topic selection for different taxonomy types
   - **Conversation Generation**: Test strategy-specific behaviors

## Code Style Guidelines
- **Python Version**: 3.10 or higher
- **Classes**: Use CamelCase (e.g., `SyntheticChatGenerator`)
- **Methods/Functions**: Use snake_case (e.g., `process_conversation`)
- **Type Hints**: Required for all functions and class attributes
- **Error Handling**: Use specific exceptions with contextual error messages
- **Documentation**: Docstrings for all classes and public methods
- **Imports**: Standard library → third-party → local modules

## Architecture Guidelines
- **Strategy Pattern**: Use a strategy pattern for different taxonomy and generation strategies
- **Base Classes**: Implement abstract base classes for key components
- **Dependency Injection**: Pass strategy implementations to constructor
- **Plugin Framework**: Design with extensibility in mind for new use cases
- **Configuration**: Separate core config from use-case specific configs