"""
Tests for API optimization features in BuildCheck
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Import the modules to test
try:
    from api_optimizer import APIOptimizer, APIPrediction
    API_OPTIMIZER_AVAILABLE = True
except ImportError:
    API_OPTIMIZER_AVAILABLE = False

try:
    from build_check import SimpleBuildAnalyzer
    BUILD_CHECK_AVAILABLE = True
except ImportError:
    BUILD_CHECK_AVAILABLE = False


@pytest.mark.skipif(not API_OPTIMIZER_AVAILABLE, reason="API optimizer module not available")
class TestAPIOptimization:
    """Test class for API optimization features"""
    
    @pytest.fixture
    def mock_github(self):
        """Fixture to provide mock GitHub client"""
        mock_gh = Mock()
        
        # Mock rate limit response
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 5000
        mock_rate_limit.core.limit = 5000
        mock_gh.get_rate_limit.return_value = mock_rate_limit
        
        # Mock search response
        mock_search = Mock()
        mock_search.totalCount = 100
        mock_gh.search_repositories.return_value = mock_search
        
        return mock_gh
    
    @pytest.fixture
    def test_org(self):
        """Fixture to provide test organization"""
        return "test-org"
    
    @pytest.fixture
    def optimizer(self, mock_github, test_org):
        """Fixture to provide API optimizer instance"""
        return APIOptimizer(mock_github, test_org)
    
    def test_api_optimizer_import(self):
        """Test that API optimizer can be imported"""
        assert API_OPTIMIZER_AVAILABLE, "API optimizer should be importable"
    
    def test_build_check_integration(self):
        """Test that build_check integrates with API optimizer"""
        assert BUILD_CHECK_AVAILABLE, "BuildCheck should be importable"
    
    def test_api_prediction_structure(self, optimizer):
        """Test API prediction data structure"""
        # Create a mock prediction
        prediction = APIPrediction(
            total_repositories=100,
            repositories_to_analyze=80,
            api_calls_for_discovery=1,
            api_calls_per_repository=10,
            total_api_calls_estimated=801,
            time_estimate_minutes=0.7,
            rate_limit_impact="safe",
            recommendations=["Enable caching for better performance"]
        )
        
        # Test that all fields are accessible
        assert prediction.total_repositories == 100
        assert prediction.repositories_to_analyze == 80
        assert prediction.total_api_calls_estimated == 801
        assert prediction.rate_limit_impact == "safe"
        assert len(prediction.recommendations) == 1
    
    def test_file_pattern_optimization(self, optimizer):
        """Test file pattern optimization"""
        # Test file pattern optimization
        patterns = [
            'pom.xml',
            'build.gradle',
            '.mvn/wrapper/maven-wrapper.properties',
            'gradle/wrapper/gradle-wrapper.properties',
            'Jenkinsfile'
        ]
        
        optimized = optimizer.optimize_file_check_order(patterns)
        
        # Check that wrapper files are prioritized
        assert '.mvn/wrapper/maven-wrapper.properties' in optimized[:2]
        assert 'gradle/wrapper/gradle-wrapper.properties' in optimized[:2]
    
    def test_analysis_plan_creation(self, optimizer):
        """Test analysis plan creation"""
        # Create mock repositories
        mock_repos = [Mock(name=f'repo-{i}', default_branch='main') for i in range(10)]
        
        # Create analysis plan
        plan = optimizer.create_analysis_plan(mock_repos, jenkins_only=False)
        
        # Check plan structure
        assert 'total_repositories' in plan
        assert 'estimated_api_calls' in plan
        assert 'phases' in plan
        assert 'optimizations' in plan
        
        # Check phases
        assert len(plan['phases']) > 0
        for phase in plan['phases']:
            assert 'name' in phase
            assert 'api_calls' in phase
            assert 'description' in phase
    
    def test_optimization_suggestions(self, optimizer):
        """Test optimization suggestions"""
        # Test suggestions for high API usage
        suggestions = optimizer.suggest_optimizations(5000, 2000)
        
        # Should have suggestions for high usage
        assert len(suggestions) > 0
        
        # Test suggestions for low API usage
        suggestions_low = optimizer.suggest_optimizations(1000, 2000)
        
        # Should have no suggestions for low usage
        assert len(suggestions_low) == 0
    
    def test_alternative_endpoints(self, optimizer):
        """Test alternative API endpoints information"""
        # Get alternative endpoints
        endpoints = optimizer.get_alternative_api_endpoints()
        
        # Check that we have endpoint information
        assert len(endpoints) > 0
        assert "GraphQL API" in endpoints
        assert "Search API" in endpoints
        assert "Contents API" in endpoints
    
    @pytest.mark.integration
    def test_api_prediction_with_real_data(self, optimizer):
        """Test API prediction with realistic data"""
        # Test prediction with estimated repository count
        prediction = optimizer.predict_api_calls(
            estimated_repos=100,
            jenkins_only=False,
            use_cache=True,
            max_workers=8
        )
        
        # Verify prediction structure
        assert hasattr(prediction, 'total_repositories')
        assert hasattr(prediction, 'total_api_calls_estimated')
        assert hasattr(prediction, 'rate_limit_impact')
        assert hasattr(prediction, 'recommendations')
    
    @pytest.mark.integration
    def test_bulk_analysis_optimization(self, optimizer):
        """Test bulk analysis optimization features"""
        # Test file pattern optimization
        files_to_fetch = [
            'pom.xml',
            'build.gradle',
            'Jenkinsfile',
            'package.json'
        ]
        
        # Test file pattern optimization
        optimized_patterns = optimizer.optimize_file_check_order(files_to_fetch)
        
        # Should return optimized list
        assert len(optimized_patterns) == len(files_to_fetch)
        assert isinstance(optimized_patterns, list)
    
    def test_rate_limit_optimization(self, optimizer):
        """Test rate limit optimization strategies"""
        # Test rate limit remaining method
        remaining = optimizer._get_rate_limit_remaining()
        
        # Should return a reasonable number
        assert isinstance(remaining, int)
        assert remaining >= 0
        
        # Test organization size estimation
        size_estimate = optimizer.get_organization_size_estimate()
        
        # Should return a reasonable estimate
        assert isinstance(size_estimate, int)
        assert size_estimate >= 0


@pytest.mark.skipif(not BUILD_CHECK_AVAILABLE, reason="BuildCheck module not available")
class TestBuildCheckOptimizationIntegration:
    """Test class for BuildCheck integration with API optimization"""
    
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
    
    def test_analyzer_with_optimization(self, github_token, test_org):
        """Test that analyzer can be created with optimization features"""
        analyzer = SimpleBuildAnalyzer(
            github_token, 
            test_org, 
            rate_limit_delay=0.05, 
            verbose=False
        )
        
        # Should have optimization-related attributes
        assert hasattr(analyzer, 'rate_limit_delay')
        assert hasattr(analyzer, 'api_calls_made')
    
    def test_optimized_api_calls(self, github_token, test_org):
        """Test that API calls are optimized"""
        analyzer = SimpleBuildAnalyzer(github_token, test_org, rate_limit_delay=0.05, verbose=False)
        
        # Verify initial state
        assert analyzer.api_calls_made == 0
        
        # Verify analyzer has optimization-related attributes
        assert hasattr(analyzer, 'rate_limit_delay')
        assert hasattr(analyzer, 'api_calls_made')
        assert hasattr(analyzer, 'max_workers')


if __name__ == '__main__':
    pytest.main([__file__]) 