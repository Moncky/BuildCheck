#!/usr/bin/env python3
"""
Configuration Manager for BuildCheck

This module handles loading and validating YAML configuration files for BuildCheck.
It provides a clean interface for the main application to access configuration settings
without having to pass numerous command line arguments.
"""

import os
import yaml
import re
import fnmatch
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParallelismConfig:
    """Configuration for parallel processing settings"""
    max_workers: int = 8
    rate_limit_delay: float = 0.05
    optimized: bool = False


@dataclass
class APIOptimizationConfig:
    """Configuration for API optimization settings"""
    predict_api_calls: bool = True
    prediction_warning_threshold: int = 3000
    bulk_analysis: bool = True
    bulk_file_limit: int = 10
    adaptive_rate_limiting: bool = True
    conservative_mode: bool = False
    strategies: Dict[str, Any] = None

    def __post_init__(self):
        if self.strategies is None:
            self.strategies = {
                'jenkins_only': True,
                'skip_archived': True,
                'skip_forks': False,
                'max_repositories': None
            }


@dataclass
class ExclusionConfig:
    """Configuration for repository exclusions"""
    repositories: List[str]
    patterns: List[str]


@dataclass
class AnalysisConfig:
    """Configuration for analysis mode settings"""
    jenkins_only: bool = False
    single_repository: Optional[str] = None


@dataclass
class CachingConfig:
    """Configuration for caching settings"""
    enabled: bool = True
    directory: str = ".cache"
    duration: int = 3600


@dataclass
class OutputConfig:
    """Configuration for output settings"""
    json_report: Optional[str] = None
    csv_report: Optional[str] = None
    html_report: Optional[str] = None
    verbose: bool = False


@dataclass
class BuildCheckConfig:
    """Main configuration class that holds all BuildCheck settings"""
    organization: str
    parallelism: ParallelismConfig
    api_optimization: APIOptimizationConfig
    exclusions: ExclusionConfig
    analysis: AnalysisConfig
    caching: CachingConfig
    output: OutputConfig
    token: Optional[str] = None

    def should_exclude_repository(self, repo_name: str) -> bool:
        """
        Check if a repository should be excluded based on configuration
        
        Args:
            repo_name: Name of the repository to check
            
        Returns:
            True if repository should be excluded, False otherwise
        """
        # Check exact repository names
        if repo_name in self.exclusions.repositories:
            return True
        
        # Check pattern-based exclusions
        for pattern in self.exclusions.patterns:
            if fnmatch.fnmatch(repo_name, pattern):
                return True
        
        return False


class ConfigManager:
    """Manages loading and validation of BuildCheck configuration files"""
    
    DEFAULT_CONFIG_FILE = "config.yaml"
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager
        
        Args:
            config_file: Path to configuration file (default: config.yaml)
        """
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self.config: Optional[BuildCheckConfig] = None
    
    def load_config(self) -> BuildCheckConfig:
        """
        Load configuration from YAML file
        
        Returns:
            BuildCheckConfig object with all settings
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file has invalid YAML
            ValueError: If required fields are missing or invalid
        """
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in configuration file: {e}")
        
        # Validate and create configuration object
        self.config = self._validate_and_create_config(config_data)
        return self.config
    
    def _validate_and_create_config(self, config_data: Dict[str, Any]) -> BuildCheckConfig:
        """
        Validate configuration data and create BuildCheckConfig object
        
        Args:
            config_data: Raw configuration data from YAML file
            
        Returns:
            Validated BuildCheckConfig object
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        if not config_data.get('organization'):
            raise ValueError("'organization' is required in configuration file")
        
        # Load parallelism configuration
        parallelism_data = config_data.get('parallelism', {})
        parallelism = ParallelismConfig(
            max_workers=parallelism_data.get('max_workers', 8),
            rate_limit_delay=parallelism_data.get('rate_limit_delay', 0.05),
            optimized=parallelism_data.get('optimized', False)
        )
        
        # Validate parallelism settings
        if parallelism.max_workers < 1 or parallelism.max_workers > 16:
            raise ValueError("max_workers must be between 1 and 16")
        if parallelism.rate_limit_delay < 0:
            raise ValueError("rate_limit_delay must be non-negative")
        
        # Load API optimization configuration
        api_optimization_data = config_data.get('api_optimization', {})
        api_optimization = APIOptimizationConfig(
            predict_api_calls=api_optimization_data.get('predict_api_calls', True),
            prediction_warning_threshold=api_optimization_data.get('prediction_warning_threshold', 3000),
            bulk_analysis=api_optimization_data.get('bulk_analysis', True),
            bulk_file_limit=api_optimization_data.get('bulk_file_limit', 10),
            adaptive_rate_limiting=api_optimization_data.get('adaptive_rate_limiting', True),
            conservative_mode=api_optimization_data.get('conservative_mode', False),
            strategies=api_optimization_data.get('strategies')
        )
        
        # Load exclusion configuration
        exclusions_data = config_data.get('exclusions', {})
        exclusions = ExclusionConfig(
            repositories=exclusions_data.get('repositories', []),
            patterns=exclusions_data.get('patterns', [])
        )
        
        # Load analysis configuration
        analysis_data = config_data.get('analysis', {})
        analysis = AnalysisConfig(
            jenkins_only=analysis_data.get('jenkins_only', False),
            single_repository=analysis_data.get('single_repository')
        )
        
        # Load caching configuration
        caching_data = config_data.get('caching', {})
        caching = CachingConfig(
            enabled=caching_data.get('enabled', True),
            directory=caching_data.get('directory', '.cache'),
            duration=caching_data.get('duration', 3600)
        )
        
        # Validate caching settings
        if caching.duration < 0:
            raise ValueError("cache duration must be non-negative")
        
        # Load output configuration
        output_data = config_data.get('output', {})
        output = OutputConfig(
            json_report=output_data.get('json_report'),
            csv_report=output_data.get('csv_report'),
            html_report=output_data.get('html_report'),
            verbose=output_data.get('verbose', False)
        )
        
        # Load token (prefer environment variable over config file for security)
        token = os.environ.get('GITHUB_TOKEN') or config_data.get('token')
        
        return BuildCheckConfig(
            organization=config_data['organization'],
            parallelism=parallelism,
            api_optimization=api_optimization,
            exclusions=exclusions,
            analysis=analysis,
            caching=caching,
            output=output,
            token=token
        )
    
    def get_config(self) -> BuildCheckConfig:
        """
        Get the current configuration, loading it if necessary
        
        Returns:
            BuildCheckConfig object
        """
        if self.config is None:
            self.config = self.load_config()
        return self.config
    
    def create_default_config(self) -> None:
        """
        Create a default configuration file if it doesn't exist
        
        This method creates a template configuration file that users can customize.
        """
        if os.path.exists(self.config_file):
            return  # Don't overwrite existing config
        
        default_config = {
            'organization': 'your-org-name',
            'parallelism': {
                'max_workers': 8,
                'rate_limit_delay': 0.05,
                'optimized': False
            },
            'api_optimization': {
                'predict_api_calls': True,
                'prediction_warning_threshold': 3000,
                'bulk_analysis': True,
                'bulk_file_limit': 10,
                'adaptive_rate_limiting': True,
                'conservative_mode': False,
                'strategies': {
                    'jenkins_only': True,
                    'skip_archived': True,
                    'skip_forks': False,
                    'max_repositories': None
                }
            },
            'exclusions': {
                'repositories': [
                    'infrastructure-environments',
                    'infrastructure-modules',
                    'documentation',
                    'wiki-content'
                ],
                'patterns': [
                    'terraform-*',
                    '*-infra',
                    'legacy-*',
                    'test-*',
                    'demo-*'
                ]
            },
            'analysis': {
                'jenkins_only': False,
                'single_repository': None
            },
            'caching': {
                'enabled': True,
                'directory': '.cache',
                'duration': 3600
            },
            'output': {
                'json_report': None,
                'csv_report': None,
                'html_report': None,
                'verbose': False
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    def validate_repository_exclusions(self, repo_names: List[str]) -> Dict[str, List[str]]:
        """
        Validate repository exclusions against a list of repository names
        
        Args:
            repo_names: List of repository names to check against
            
        Returns:
            Dictionary with 'excluded' and 'included' repository lists
        """
        if self.config is None:
            self.config = self.load_config()
        
        excluded = []
        included = []
        
        for repo_name in repo_names:
            if self.config.should_exclude_repository(repo_name):
                excluded.append(repo_name)
            else:
                included.append(repo_name)
        
        return {
            'excluded': excluded,
            'included': included
        }


def load_config_from_file(config_file: Optional[str] = None) -> BuildCheckConfig:
    """
    Convenience function to load configuration from file
    
    Args:
        config_file: Path to configuration file (default: config.yaml)
        
    Returns:
        BuildCheckConfig object
    """
    manager = ConfigManager(config_file)
    return manager.load_config()


def create_default_config_file(config_file: Optional[str] = None) -> None:
    """
    Convenience function to create default configuration file
    
    Args:
        config_file: Path to configuration file (default: config.yaml)
    """
    manager = ConfigManager(config_file)
    manager.create_default_config() 