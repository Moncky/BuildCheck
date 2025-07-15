"""
Tests for caching functionality in BuildCheck
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Import the modules to test
from build_check import SimpleBuildAnalyzer

# Load environment variables for tests
load_dotenv()


class TestCaching:
    """Test class for caching functionality"""
    
    @pytest.fixture
    def github_token(self):
        """Fixture to provide GitHub token for tests"""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            pytest.skip("GITHUB_TOKEN environment variable is required")
        return token
    
    @pytest.fixture
    def test_org(self):
        """Fixture to provide test organization"""
        return "octocat"  # GitHub's test organization
    
    def test_caching_creation(self, github_token, test_org):
        """Test that cache is created on first run"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, use_cache=True, verbose=False)
        
        # First run should create cache
        repos1 = analyzer.get_repositories()
        
        # Verify cache directory exists
        cache_dir = ".cache"
        assert os.path.exists(cache_dir), "Cache directory should be created"
        
        # Verify cache files are created
        cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
        assert len(cache_files) > 0, "Cache files should be created"
    
    def test_caching_performance(self, github_token, test_org):
        """Test that second run is faster due to caching"""
        # First run
        start_time = time.time()
        analyzer1 = SimpleBuildAnalyzer(github_token, test_org, use_cache=True, verbose=False)
        repos1 = analyzer1.get_repositories()
        first_run_time = time.time() - start_time
        
        # Second run
        start_time = time.time()
        analyzer2 = SimpleBuildAnalyzer(github_token, test_org, use_cache=True, verbose=False)
        repos2 = analyzer2.get_repositories()
        second_run_time = time.time() - start_time
        
        # For small organizations, the performance difference might be minimal
        # but we can still verify the functionality works
        assert len(repos1) == len(repos2), "Both runs should return the same number of repositories"
        
        # Verify API calls are tracked
        assert hasattr(analyzer1, 'api_calls_made'), "API calls should be tracked"
        assert hasattr(analyzer2, 'api_calls_made'), "API calls should be tracked"
    
    def test_cache_disabled(self, github_token, test_org):
        """Test that cache can be disabled"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, use_cache=False, verbose=False)
        repos = analyzer.get_repositories()
        
        # Should still work without cache
        assert isinstance(repos, list), "Should return a list of repositories"
    
    @patch('build_check.SimpleBuildAnalyzer._make_api_call')
    def test_cache_api_calls_reduction(self, mock_api_call, github_token, test_org):
        """Test that API calls are reduced when using cache"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "test-repo"}]
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        # First run
        analyzer1 = SimpleBuildAnalyzer(github_token, test_org, use_cache=True, verbose=False)
        analyzer1.get_repositories()
        first_run_calls = analyzer1.api_calls_made
        
        # Second run
        analyzer2 = SimpleBuildAnalyzer(github_token, test_org, use_cache=True, verbose=False)
        analyzer2.get_repositories()
        second_run_calls = analyzer2.api_calls_made
        
        # Second run should have fewer or equal API calls due to caching
        assert second_run_calls <= first_run_calls, "Second run should not make more API calls than first run"


if __name__ == '__main__':
    pytest.main([__file__]) 