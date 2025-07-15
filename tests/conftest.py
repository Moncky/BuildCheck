"""
Shared pytest configuration and fixtures for BuildCheck tests
"""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables for all tests
load_dotenv()


@pytest.fixture(scope="session")
def github_token():
    """Session-scoped fixture to provide GitHub token for all tests"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        pytest.skip("GITHUB_TOKEN environment variable is required for tests")
    return token


@pytest.fixture(scope="session")
def test_org():
    """Session-scoped fixture to provide test organization"""
    return "octocat"  # GitHub's test organization


@pytest.fixture(scope="function")
def cache_cleanup():
    """Function-scoped fixture to clean up cache before and after tests"""
    cache_dir = ".cache"
    
    # Clean up before test
    if os.path.exists(cache_dir):
        for file in os.listdir(cache_dir):
            if file.endswith('.pkl'):
                os.remove(os.path.join(cache_dir, file))
    
    yield
    
    # Clean up after test
    if os.path.exists(cache_dir):
        for file in os.listdir(cache_dir):
            if file.endswith('.pkl'):
                os.remove(os.path.join(cache_dir, file))


@pytest.fixture(scope="function")
def mock_api_response():
    """Function-scoped fixture to provide a mock API response"""
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.json.return_value = [{"name": "test-repo"}]
    mock_response.status_code = 200
    mock_response.headers = {
        'X-RateLimit-Remaining': '4999',
        'X-RateLimit-Limit': '5000',
        'X-RateLimit-Reset': '1234567890'
    }
    return mock_response 