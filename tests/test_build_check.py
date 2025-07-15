"""
Tests for the main build_check module functionality
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Import the modules to test
from build_check import BuildAnalyzer, SimpleBuildAnalyzer

# Load environment variables for tests
load_dotenv()


class TestBuildAnalyzer:
    """Test class for BuildAnalyzer functionality"""
    
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
    
    def test_build_analyzer_initialization(self, github_token, test_org):
        """Test that BuildAnalyzer can be initialized correctly"""
        analyzer = BuildAnalyzer(github_token, test_org)
        
        assert analyzer.token == github_token, "Token should be set correctly"
        assert analyzer.organization == test_org, "Organization should be set correctly"
        assert hasattr(analyzer, 'api_calls_made'), "API calls should be tracked"
        assert analyzer.api_calls_made == 0, "Initial API calls should be 0"
    
    def test_build_analyzer_with_options(self, github_token, test_org):
        """Test that BuildAnalyzer accepts optional parameters"""
        analyzer = BuildAnalyzer(
            github_token, 
            test_org, 
            rate_limit_delay=0.1,
            verbose=True
        )
        
        assert analyzer.rate_limit_delay == 0.1, "Rate limit delay should be set"
        assert analyzer.verbose is True, "Verbose mode should be set"
    
    @patch('build_check.BuildAnalyzer._make_api_call')
    def test_get_repositories(self, mock_api_call, github_token, test_org):
        """Test that get_repositories method works correctly"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": "repo1", "full_name": "test-org/repo1"},
            {"name": "repo2", "full_name": "test-org/repo2"}
        ]
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        analyzer = BuildAnalyzer(github_token, test_org)
        repos = analyzer.get_repositories()
        
        assert isinstance(repos, list), "Should return a list"
        assert len(repos) == 2, "Should return correct number of repositories"
        assert repos[0]["name"] == "repo1", "Should return correct repository data"
    
    @patch('build_check.BuildAnalyzer._make_api_call')
    def test_get_workflow_files(self, mock_api_call, github_token, test_org):
        """Test that get_workflow_files method works correctly"""
        # Mock API response for workflow files
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tree": [
                {"path": ".github/workflows/ci.yml", "type": "blob"},
                {"path": ".github/workflows/deploy.yml", "type": "blob"}
            ]
        }
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        analyzer = BuildAnalyzer(github_token, test_org)
        workflow_files = analyzer.get_workflow_files("test-repo")
        
        assert isinstance(workflow_files, list), "Should return a list"
        assert len(workflow_files) == 2, "Should return correct number of workflow files"
        assert any("ci.yml" in f for f in workflow_files), "Should include CI workflow"


class TestSimpleBuildAnalyzer:
    """Test class for SimpleBuildAnalyzer functionality"""
    
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
    
    def test_simple_build_analyzer_initialization(self, github_token, test_org):
        """Test that SimpleBuildAnalyzer can be initialized correctly"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org)
        
        assert analyzer.token == github_token, "Token should be set correctly"
        assert analyzer.organization == test_org, "Organization should be set correctly"
        assert hasattr(analyzer, 'api_calls_made'), "API calls should be tracked"
        assert analyzer.api_calls_made == 0, "Initial API calls should be 0"
    
    def test_simple_build_analyzer_with_cache(self, github_token, test_org):
        """Test that SimpleBuildAnalyzer works with caching"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, use_cache=True)
        
        assert hasattr(analyzer, 'use_cache'), "Cache option should be configurable"
        assert analyzer.use_cache is True, "Cache should be enabled"
    
    @patch('build_check.SimpleBuildAnalyzer._make_api_call')
    def test_get_repositories_simple(self, mock_api_call, github_token, test_org):
        """Test that SimpleBuildAnalyzer get_repositories works"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"name": "repo1", "full_name": "test-org/repo1"},
            {"name": "repo2", "full_name": "test-org/repo2"}
        ]
        mock_response.status_code = 200
        mock_api_call.return_value = mock_response
        
        analyzer = SimpleBuildAnalyzer(github_token, test_org)
        repos = analyzer.get_repositories()
        
        assert isinstance(repos, list), "Should return a list"
        assert len(repos) == 2, "Should return correct number of repositories"
    
    def test_verbose_output(self, github_token, test_org):
        """Test that verbose output can be configured"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, verbose=True)
        
        assert analyzer.verbose is True, "Verbose mode should be enabled"
    
    def test_rate_limit_delay_configuration(self, github_token, test_org):
        """Test that rate limit delay can be configured"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.05)
        
        assert analyzer.rate_limit_delay == 0.05, "Rate limit delay should be set correctly"
    
    def test_get_specific_repository_success(self, github_token, test_org):
        """Test that get_specific_repository works when repository exists"""
        with patch('build_check.Github') as mock_github:
            # Mock the GitHub client and organization
            mock_github_instance = MagicMock()
            mock_org = MagicMock()
            mock_repo = MagicMock()
            mock_repo.name = "test-repo"
            mock_repo.archived = False
            
            mock_github_instance.get_organization.return_value = mock_org
            mock_org.get_repo.return_value = mock_repo
            mock_github.return_value = mock_github_instance
            
            analyzer = SimpleBuildAnalyzer(github_token, test_org)
            repo = analyzer.get_specific_repository("test-repo")
            
            assert repo is not None, "Should return repository when it exists"
            assert repo.name == "test-repo", "Should return correct repository name"
            mock_org.get_repo.assert_called_once_with("test-repo")
    
    def test_get_specific_repository_not_found(self, github_token, test_org):
        """Test that get_specific_repository returns None when repository doesn't exist"""
        from github import GithubException
        
        with patch('build_check.Github') as mock_github:
            # Mock the GitHub client and organization
            mock_github_instance = MagicMock()
            mock_org = MagicMock()
            
            mock_github_instance.get_organization.return_value = mock_org
            mock_org.get_repo.side_effect = GithubException(404, "Not Found")
            mock_github.return_value = mock_github_instance
            
            analyzer = SimpleBuildAnalyzer(github_token, test_org)
            repo = analyzer.get_specific_repository("non-existent-repo")
            
            assert repo is None, "Should return None when repository doesn't exist"
            mock_org.get_repo.assert_called_once_with("non-existent-repo")
    
    def test_get_specific_repository_archived(self, github_token, test_org):
        """Test that get_specific_repository handles archived repositories"""
        with patch('build_check.Github') as mock_github:
            # Mock the GitHub client and organization
            mock_github_instance = MagicMock()
            mock_org = MagicMock()
            mock_repo = MagicMock()
            mock_repo.name = "archived-repo"
            mock_repo.archived = True
            
            mock_github_instance.get_organization.return_value = mock_org
            mock_org.get_repo.return_value = mock_repo
            mock_github.return_value = mock_github_instance
            
            analyzer = SimpleBuildAnalyzer(github_token, test_org)
            repo = analyzer.get_specific_repository("archived-repo")
            
            assert repo is not None, "Should return repository even if archived"
            assert repo.archived is True, "Should correctly identify archived repository"


class TestIntegration:
    """Integration tests that test multiple components together"""
    
    @pytest.mark.integration
    def test_full_workflow(self, github_token, test_org):
        """Test a complete workflow from initialization to data retrieval"""
        # This test would normally make real API calls
        # For now, we'll test the basic structure
        analyzer = SimpleBuildAnalyzer(github_token, test_org, use_cache=False)
        
        assert analyzer is not None, "Analyzer should be created"
        assert hasattr(analyzer, 'get_repositories'), "Should have get_repositories method"
        assert hasattr(analyzer, '_make_api_call'), "Should have _make_api_call method"
    
    @pytest.mark.slow
    def test_cache_integration(self, github_token, test_org, cache_cleanup):
        """Test that caching works in a real scenario"""
        # This test would normally make real API calls and test caching
        # For now, we'll test the basic structure
        analyzer1 = SimpleBuildAnalyzer(github_token, test_org, use_cache=True)
        analyzer2 = SimpleBuildAnalyzer(github_token, test_org, use_cache=True)
        
        assert analyzer1.use_cache is True, "First analyzer should use cache"
        assert analyzer2.use_cache is True, "Second analyzer should use cache"


if __name__ == '__main__':
    pytest.main([__file__]) 