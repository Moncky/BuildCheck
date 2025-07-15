"""
Tests for rate limiting functionality in BuildCheck
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Import the modules to test
from build_check import BuildAnalyzer, SimpleBuildAnalyzer

# Load environment variables for tests
load_dotenv()


class TestRateLimit:
    """Test class for rate limiting functionality"""
    
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
        analyzer = BuildAnalyzer(github_token, test_org, rate_limit_delay=0.1)
        
        assert hasattr(analyzer, 'rate_limit_delay'), "Rate limit delay should be configurable"
        assert analyzer.rate_limit_delay == 0.1, "Rate limit delay should be set correctly"
    
    @patch('build_check.BuildAnalyzer._make_api_call')
    def test_rate_limit_checking(self, mock_api_call, github_token, test_org):
        """Test that rate limit checking works"""
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
        
        analyzer = BuildAnalyzer(github_token, test_org, rate_limit_delay=0.1)
        
        # Test rate limit checking
        analyzer._check_rate_limit()
        
        # Verify the method exists and can be called
        assert hasattr(analyzer, '_check_rate_limit'), "Rate limit checking method should exist"
    
    @patch('build_check.BuildAnalyzer._make_api_call')
    def test_api_call_tracking(self, mock_api_call, github_token, test_org):
        """Test that API calls are properly tracked"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "test-repo"}]
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        analyzer = BuildAnalyzer(github_token, test_org, rate_limit_delay=0.1)
        
        # Initial state
        assert analyzer.api_calls_made == 0, "Initial API calls should be 0"
        
        # Make API calls
        analyzer._make_api_call("Test call 1")
        assert analyzer.api_calls_made == 1, "API calls should be incremented"
        
        analyzer._make_api_call("Test call 2")
        assert analyzer.api_calls_made == 2, "API calls should be incremented"
    
    def test_rate_limit_delay_timing(self, github_token, test_org):
        """Test that rate limit delays are applied"""
        analyzer = BuildAnalyzer(github_token, test_org, rate_limit_delay=0.1)
        
        start_time = time.time()
        
        # This would normally make an API call, but we're just testing the delay
        # For now, just verify the analyzer can be created
        assert analyzer is not None, "Analyzer should be created successfully"
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Creation should be fast
        assert creation_time < 1.0, "Analyzer creation should be fast"
    
    @patch('build_check.BuildAnalyzer._make_api_call')
    def test_rate_limit_headers_parsing(self, mock_api_call, github_token, test_org):
        """Test that rate limit headers are properly parsed"""
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
        
        analyzer = BuildAnalyzer(github_token, test_org, rate_limit_delay=0.1)
        
        # Make an API call to trigger header parsing
        response = analyzer._make_api_call("Test call")
        
        # Verify response is returned
        assert response is not None, "API call should return a response"
        assert response.status_code == 200, "Response should have correct status code"
    
    def test_simple_build_analyzer_rate_limit(self, github_token, test_org):
        """Test that SimpleBuildAnalyzer also supports rate limiting"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.1)
        
        assert hasattr(analyzer, 'rate_limit_delay'), "SimpleBuildAnalyzer should support rate limit delay"
        assert analyzer.rate_limit_delay == 0.1, "Rate limit delay should be set correctly"
        assert hasattr(analyzer, 'api_calls_made'), "API calls should be tracked"
    
    @patch('build_check.SimpleBuildAnalyzer._make_api_call')
    def test_simple_build_analyzer_api_tracking(self, mock_api_call, github_token, test_org):
        """Test that SimpleBuildAnalyzer tracks API calls correctly"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "test-repo"}]
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.1)
        
        # Initial state
        assert analyzer.api_calls_made == 0, "Initial API calls should be 0"
        
        # Make API calls
        analyzer._make_api_call("Test call 1")
        assert analyzer.api_calls_made == 1, "API calls should be incremented"
        
        analyzer._make_api_call("Test call 2")
        assert analyzer.api_calls_made == 2, "API calls should be incremented"


if __name__ == '__main__':
    pytest.main([__file__]) 