# BuildCheck Tests

This directory contains the test suite for the BuildCheck project, organized according to Python best practices.

## Test Structure

```
tests/
├── __init__.py              # Makes tests a Python package
├── conftest.py              # Shared fixtures and configuration
├── test_build_check.py      # Tests for main build_check module
├── test_caching.py          # Tests for caching functionality
├── test_performance.py      # Tests for performance optimizations
├── test_rate_limit.py       # Tests for rate limiting functionality
└── README.md               # This file
```

## Running Tests

### Using the test runner script (recommended)
```bash
# Run all tests
./run_tests.sh

# Run tests with coverage
./run_tests.sh --coverage

# Run tests with verbose output
./run_tests.sh --verbose

# Run only unit tests
./run_tests.sh --unit

# Run only integration tests
./run_tests.sh --integration

# Run only slow tests
./run_tests.sh --slow
```

### Using pytest directly
```bash
# Run all tests
python -m pytest tests/

# Run tests with coverage
python -m pytest tests/ --cov=build_check --cov=cache_manager --cov=jenkins_analyzer --cov-report=html

# Run specific test file
python -m pytest tests/test_caching.py

# Run specific test class
python -m pytest tests/test_caching.py::TestCaching

# Run specific test method
python -m pytest tests/test_caching.py::TestCaching::test_caching_creation
```

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Use mocking to avoid external dependencies
- Fast execution
- Marked with `@pytest.mark.unit`

### Integration Tests
- Test multiple components working together
- May make real API calls (with proper rate limiting)
- Slower execution
- Marked with `@pytest.mark.integration`

### Slow Tests
- Tests that take significant time to run
- Usually involve real API calls or complex operations
- Marked with `@pytest.mark.slow`

## Test Fixtures

Shared fixtures are defined in `conftest.py`:

- `github_token`: Session-scoped fixture providing GitHub API token
- `test_org`: Session-scoped fixture providing test organization
- `cache_cleanup`: Function-scoped fixture for cleaning up cache files
- `mock_api_response`: Function-scoped fixture providing mock API responses

## Environment Variables

Tests require the following environment variables:

- `GITHUB_TOKEN`: GitHub API token for authentication

You can set these in a `.env` file in the project root:

```bash
GITHUB_TOKEN=your_github_token_here
```

## Test Dependencies

Test dependencies are included in `requirements.txt`:

- `pytest`: Test framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking utilities

## Best Practices

1. **Use descriptive test names**: Test methods should clearly describe what they're testing
2. **One assertion per test**: Each test should verify one specific behavior
3. **Use fixtures**: Share common setup code using pytest fixtures
4. **Mock external dependencies**: Use mocking to avoid real API calls in unit tests
5. **Clean up after tests**: Use fixtures to clean up any files or state created during tests
6. **Skip tests when appropriate**: Use `pytest.skip()` when required dependencies are missing

## Coverage

To generate a coverage report:

```bash
./run_tests.sh --coverage
```

This will create an HTML coverage report in `htmlcov/index.html` showing which lines of code are tested.

## Continuous Integration

The test suite is designed to work with CI/CD pipelines. Tests will:

- Skip gracefully when required environment variables are missing
- Use mocking to avoid external dependencies in unit tests
- Provide clear error messages when tests fail
- Generate coverage reports for quality metrics 