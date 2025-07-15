#!/bin/bash

# Test runner script for BuildCheck
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
PYTEST_OPTS=""
COVERAGE=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            PYTEST_OPTS="$PYTEST_OPTS -v"
            shift
            ;;
        --unit)
            PYTEST_OPTS="$PYTEST_OPTS -m unit"
            shift
            ;;
        --integration)
            PYTEST_OPTS="$PYTEST_OPTS -m integration"
            shift
            ;;
        --slow)
            PYTEST_OPTS="$PYTEST_OPTS -m slow"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --coverage          Run tests with coverage report"
            echo "  --verbose, -v       Verbose output"
            echo "  --unit              Run only unit tests"
            echo "  --integration       Run only integration tests"
            echo "  --slow              Run only slow tests"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests"
            echo "  $0 --coverage         # Run tests with coverage"
            echo "  $0 --unit --verbose   # Run unit tests with verbose output"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}Running BuildCheck tests...${NC}"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Warning: Virtual environment not detected${NC}"
    echo "Consider activating your virtual environment first"
fi

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -r requirements.txt
fi

# Run tests
if [ "$COVERAGE" = true ]; then
    echo -e "${BLUE}Running tests with coverage...${NC}"
    python -m pytest tests/ --cov=build_check --cov=cache_manager --cov=jenkins_analyzer --cov-report=term-missing --cov-report=html $PYTEST_OPTS
else
    echo -e "${BLUE}Running tests...${NC}"
    python -m pytest tests/ $PYTEST_OPTS
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    if [ "$COVERAGE" = true ]; then
        echo -e "${BLUE}Coverage report generated in htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi 