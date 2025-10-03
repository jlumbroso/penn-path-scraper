# Testing Guide

This document describes the testing infrastructure and available test commands.

## Test Structure

```
tests/
├── unit/              # Fast, isolated unit tests with mocked dependencies
│   ├── test_api_client.py      # API client tests (15 tests)
│   ├── test_parsers.py         # HTML parsing tests (26 tests)
│   └── test_persistence.py     # Database persistence tests (10 tests)
└── integration/       # End-to-end tests against real systems (future)
```

## Available Commands

### Basic Testing

```bash
# Run all unit tests (default)
pipenv run test
pipenv run test-unit

# Run integration tests
pipenv run test-integration

# Run all tests (unit + integration)
pipenv run test-all

# Fast fail: stop on first failure
pipenv run check-fast
```

### Coverage Reports

```bash
# Run tests with coverage report
pipenv run coverage

# Generate HTML coverage report (opens in browser)
pipenv run coverage-html
open htmlcov/index.html

# Coverage for all tests (unit + integration)
pipenv run coverage-all
```

### Performance

```bash
# Run tests in parallel (fast)
pipenv run test-parallel
```

### Type Checking

```bash
# Run mypy type checker
pipenv run typecheck
```

## Current Test Status

- **51 unit tests** - All passing
- **92% code coverage**
- **0 warnings**

### Coverage by Module

| Module              | Coverage | Missing Lines         |
|---------------------|----------|-----------------------|
| src/api_client.py   | 94%      | Error handling paths  |
| src/models.py       | 92%      | Utility functions     |
| src/parsers.py      | 91%      | Edge cases            |
| src/persistence.py  | 92%      | Database init         |
| src/types.py        | 93%      | Type definitions      |

## Writing Tests

### Unit Tests

Unit tests use pytest with mocked dependencies:

```python
import pytest

def test_something(mocker):
    # Mock external dependencies
    mock_api = mocker.patch("requests.post")
    mock_api.return_value.json.return_value = {"data": "value"}

    # Test your code
    result = your_function()

    # Assert expectations
    assert result == expected
```

### Test Fixtures

Common fixtures are defined in test files:

- `db` - In-memory SQLite database for persistence tests
- `api_client` - Configured API client instance
- `sample_api_details` - Sample API response data
- `sample_api_search_result` - Sample search results

### Best Practices

1. **Fast tests** - Unit tests should run in < 10 seconds total
2. **Isolated** - Each test should be independent
3. **Clear names** - Test names should describe what they verify
4. **AAA pattern** - Arrange, Act, Assert
5. **Mock external calls** - Never hit real APIs in unit tests

## Integration Tests

Integration tests (future) will:
- Test against real Penn Courses API
- Verify database persistence end-to-end
- Test CLI commands
- Validate exported JSON structure

These tests are slower and may require network access.

## Continuous Integration

When CI is set up:
- All unit tests must pass
- Coverage must be >= 90%
- Type checking must pass
- No warnings allowed
