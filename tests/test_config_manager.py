#!/usr/bin/env python3
"""
Tests for the configuration manager module
"""

import pytest
import tempfile
import os
import yaml
from unittest.mock import patch

# Import the configuration manager
try:
    from config_manager import (
        ConfigManager, 
        BuildCheckConfig, 
        ParallelismConfig, 
        ExclusionConfig, 
        AnalysisConfig, 
        CachingConfig, 
        OutputConfig
    )
except ImportError:
    pytest.skip("config_manager module not available", allow_module_level=True)


class TestConfigManager:
    """Test cases for the configuration manager"""
    
    def test_create_default_config(self):
        """Test creating a default configuration file"""
        config_file = tempfile.mktemp(suffix='.yaml')
        
        try:
            config_manager = ConfigManager(config_file)
            config_manager.create_default_config()
            
            # Verify file was created
            assert os.path.exists(config_file)
            
            # Verify file contains valid YAML
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            assert 'organization' in config_data
            assert config_data['organization'] == 'your-org-name'
            assert 'parallelism' in config_data
            assert 'exclusions' in config_data
            assert 'analysis' in config_data
            assert 'caching' in config_data
            assert 'output' in config_data
            
        finally:
            if os.path.exists(config_file):
                os.unlink(config_file)
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file"""
        config_data = {
            'organization': 'test-org',
            'parallelism': {
                'max_workers': 4,
                'rate_limit_delay': 0.1,
                'optimized': True
            },
            'exclusions': {
                'repositories': ['test-repo'],
                'patterns': ['test-*']
            },
            'analysis': {
                'jenkins_only': True,
                'single_repository': None
            },
            'caching': {
                'enabled': False,
                'directory': '/tmp/cache',
                'duration': 1800
            },
            'output': {
                'json_report': 'test.json',
                'verbose': True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            config_manager = ConfigManager(config_file)
            config = config_manager.load_config()
            
            assert config.organization == 'test-org'
            assert config.parallelism.max_workers == 4
            assert config.parallelism.rate_limit_delay == 0.1
            assert config.parallelism.optimized is True
            assert config.exclusions.repositories == ['test-repo']
            assert config.exclusions.patterns == ['test-*']
            assert config.analysis.jenkins_only is True
            assert config.caching.enabled is False
            assert config.caching.directory == '/tmp/cache'
            assert config.output.json_report == 'test.json'
            assert config.output.verbose is True
            
        finally:
            if os.path.exists(config_file):
                os.unlink(config_file)
    
    def test_load_config_with_defaults(self):
        """Test loading configuration with missing optional fields"""
        config_data = {
            'organization': 'test-org'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            config_manager = ConfigManager(config_file)
            config = config_manager.load_config()
            
            # Should use defaults for missing fields
            assert config.organization == 'test-org'
            assert config.parallelism.max_workers == 8
            assert config.parallelism.rate_limit_delay == 0.05
            assert config.parallelism.optimized is False
            assert config.exclusions.repositories == []
            assert config.exclusions.patterns == []
            assert config.analysis.jenkins_only is False
            assert config.caching.enabled is True
            assert config.output.verbose is False
            
        finally:
            if os.path.exists(config_file):
                os.unlink(config_file)
    
    def test_load_config_missing_organization(self):
        """Test loading configuration without required organization field"""
        config_data = {
            'parallelism': {'max_workers': 4}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            config_manager = ConfigManager(config_file)
            with pytest.raises(ValueError, match="'organization' is required"):
                config_manager.load_config()
        finally:
            if os.path.exists(config_file):
                os.unlink(config_file)
    
    def test_load_config_invalid_parallelism(self):
        """Test loading configuration with invalid parallelism settings"""
        config_data = {
            'organization': 'test-org',
            'parallelism': {
                'max_workers': 20,  # Invalid: too high
                'rate_limit_delay': -0.1  # Invalid: negative
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            config_manager = ConfigManager(config_file)
            with pytest.raises(ValueError, match="max_workers must be between 1 and 16"):
                config_manager.load_config()
        finally:
            if os.path.exists(config_file):
                os.unlink(config_file)
    
    def test_should_exclude_repository(self):
        """Test repository exclusion logic"""
        config = BuildCheckConfig(
            organization='test-org',
            parallelism=ParallelismConfig(),
            exclusions=ExclusionConfig(
                repositories=['exact-repo'],
                patterns=['test-*', '*-demo']
            ),
            analysis=AnalysisConfig(),
            caching=CachingConfig(),
            output=OutputConfig()
        )
        
        # Test exact repository exclusion
        assert config.should_exclude_repository('exact-repo') is True
        assert config.should_exclude_repository('other-repo') is False
        
        # Test pattern-based exclusion
        assert config.should_exclude_repository('test-repo') is True
        assert config.should_exclude_repository('my-demo') is True
        assert config.should_exclude_repository('production-app') is False
    
    def test_validate_repository_exclusions(self):
        """Test repository exclusion validation"""
        config_manager = ConfigManager()
        config_manager.config = BuildCheckConfig(
            organization='test-org',
            parallelism=ParallelismConfig(),
            exclusions=ExclusionConfig(
                repositories=['exact-repo'],
                patterns=['test-*']
            ),
            analysis=AnalysisConfig(),
            caching=CachingConfig(),
            output=OutputConfig()
        )
        
        repo_names = ['exact-repo', 'test-repo', 'production-app', 'test-app']
        result = config_manager.validate_repository_exclusions(repo_names)
        
        assert 'exact-repo' in result['excluded']
        assert 'test-repo' in result['excluded']
        assert 'test-app' in result['excluded']
        assert 'production-app' in result['included']
        assert len(result['excluded']) == 3
        assert len(result['included']) == 1


class TestBuildCheckConfig:
    """Test cases for the BuildCheckConfig class"""
    
    def test_should_exclude_repository_empty_exclusions(self):
        """Test exclusion logic with empty exclusion lists"""
        config = BuildCheckConfig(
            organization='test-org',
            parallelism=ParallelismConfig(),
            exclusions=ExclusionConfig(repositories=[], patterns=[]),
            analysis=AnalysisConfig(),
            caching=CachingConfig(),
            output=OutputConfig()
        )
        
        # Should not exclude any repositories
        assert config.should_exclude_repository('any-repo') is False
        assert config.should_exclude_repository('test-repo') is False
    
    def test_should_exclude_repository_complex_patterns(self):
        """Test exclusion logic with complex patterns"""
        config = BuildCheckConfig(
            organization='test-org',
            parallelism=ParallelismConfig(),
            exclusions=ExclusionConfig(
                repositories=['legacy-app'],
                patterns=['*-infra', 'terraform-*', 'demo-*', 'test-*']
            ),
            analysis=AnalysisConfig(),
            caching=CachingConfig(),
            output=OutputConfig()
        )
        
        # Test various patterns
        assert config.should_exclude_repository('legacy-app') is True  # Exact match
        assert config.should_exclude_repository('my-infra') is True    # *-infra pattern
        assert config.should_exclude_repository('terraform-aws') is True  # terraform-* pattern
        assert config.should_exclude_repository('demo-app') is True    # demo-* pattern
        assert config.should_exclude_repository('test-repo') is True   # test-* pattern
        assert config.should_exclude_repository('production-app') is False  # No match


if __name__ == '__main__':
    pytest.main([__file__]) 