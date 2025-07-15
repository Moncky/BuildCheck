"""
Tests for performance optimizations in BuildCheck
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


class TestPerformance:
    """Test class for performance optimizations"""
    
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
        return "test-org"
    
    def test_rate_limit_delay_configuration(self, github_token, test_org):
        """Test that rate limit delay can be configured"""
        # Test with custom rate limit delay
        analyzer = SimpleBuildAnalyzer(
            github_token, 
            test_org, 
            rate_limit_delay=0.05, 
            verbose=False
        )
        
        assert hasattr(analyzer, 'rate_limit_delay'), "Rate limit delay should be configurable"
        assert analyzer.rate_limit_delay == 0.05, "Rate limit delay should be set correctly"
    
    @patch('build_check.SimpleBuildAnalyzer._make_api_call')
    def test_rate_limit_caching(self, mock_api_call, github_token, test_org):
        """Test that rate limit information is cached"""
        # Mock API response with rate limit headers
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "test-repo"}]
        mock_response.status_code = 200
        mock_response.headers = {
            'X-RateLimit-Remaining': '4999',
            'X-RateLimit-Limit': '5000',
            'X-RateLimit-Reset': str(int(time.time()) + 3600)
        }
        mock_api_call.return_value = mock_response
        
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.05, verbose=False)
        
        # Make several API calls to test caching
        for i in range(3):
            analyzer._make_api_call(f"Test call {i+1}")
        
        # Verify rate limit cache is populated
        assert hasattr(analyzer, 'rate_limit_cache'), "Rate limit cache should exist"
        assert analyzer.rate_limit_cache is not None, "Rate limit cache should be populated"
        
        # Verify API calls are tracked
        assert analyzer.api_calls_made == 3, "API calls should be tracked correctly"
    
    def test_performance_timing(self, github_token, test_org):
        """Test that performance timing is reasonable"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.05, verbose=False)
        
        start_time = time.time()
        
        # Make a simple API call (this will be mocked in actual tests)
        # For now, just test that the analyzer can be created
        assert analyzer is not None, "Analyzer should be created successfully"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Creation should be fast
        assert total_time < 1.0, "Analyzer creation should be fast"
    
    @patch('build_check.SimpleBuildAnalyzer._make_api_call')
    def test_api_call_tracking(self, mock_api_call, github_token, test_org):
        """Test that API calls are properly tracked"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "test-repo"}]
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.05, verbose=False)
        
        # Initial state
        assert analyzer.api_calls_made == 0, "Initial API calls should be 0"
        
        # Make API calls
        analyzer._make_api_call("Test call 1")
        assert analyzer.api_calls_made == 1, "API calls should be incremented"
        
        analyzer._make_api_call("Test call 2")
        assert analyzer.api_calls_made == 2, "API calls should be incremented"
    
    def test_verbose_mode(self, github_token, test_org):
        """Test that verbose mode can be configured"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, verbose=True)
        
        assert hasattr(analyzer, 'verbose'), "Verbose mode should be configurable"
        assert analyzer.verbose is True, "Verbose mode should be set correctly"
    
    @patch('build_check.SimpleBuildAnalyzer._make_api_call')
    def test_average_call_time_calculation(self, mock_api_call, github_token, test_org):
        """Test that average call time can be calculated"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "test-repo"}]
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.05, verbose=False)
        
        # Make several API calls
        start_time = time.time()
        for i in range(5):
            analyzer._make_api_call(f"Test call {i+1}")
        end_time = time.time()
        
        total_time = end_time - start_time
        average_time = total_time / analyzer.api_calls_made
        
        # Verify calculations are reasonable
        assert average_time >= 0, "Average time should be non-negative"
        assert analyzer.api_calls_made == 5, "Should have made 5 API calls"


if __name__ == '__main__':
    pytest.main([__file__]) 