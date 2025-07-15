#!/usr/bin/env python3
"""
BuildCheck Configuration Setup Script

This script helps users quickly set up their BuildCheck configuration file
with their organization name and other common settings.
"""

import os
import sys
import click
from pathlib import Path

try:
    from config_manager import ConfigManager, create_default_config_file
except ImportError:
    print("Error: config_manager module not found. Please ensure it's in the same directory.")
    sys.exit(1)


@click.command()
@click.option('--org', prompt='GitHub organization name', help='GitHub organization to analyze')
@click.option('--config', default='config.yaml', help='Path to configuration file (default: config.yaml)')
@click.option('--jenkins-only', is_flag=True, help='Set Jenkins-only mode by default')
@click.option('--max-workers', default=8, help='Number of parallel workers (default: 8)')
@click.option('--verbose', is_flag=True, help='Enable verbose logging by default')
@click.option('--output', help='Default output file for JSON reports')
def setup(org: str, config: str, jenkins_only: bool, max_workers: int, verbose: bool, output: str):
    """
    Set up BuildCheck configuration file with your organization settings
    
    This script creates a configuration file with your organization name and
    other common settings, making it easy to run BuildCheck without command
    line arguments.
    """
    
    # Check if config file already exists
    if os.path.exists(config):
        if not click.confirm(f"Configuration file {config} already exists. Overwrite it?"):
            print("Setup cancelled.")
            return
    
    try:
        # Create the configuration manager
        config_manager = ConfigManager(config)
        
        # Create default config structure
        config_data = {
            'organization': org,
            'parallelism': {
                'max_workers': max_workers,
                'rate_limit_delay': 0.05
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
                'jenkins_only': jenkins_only,
                'single_repository': None
            },
            'caching': {
                'enabled': True,
                'directory': '.cache',
                'duration': 3600
            },
            'output': {
                'json_report': output,
                'verbose': verbose
            }
        }
        
        # Write the configuration file
        import yaml
        with open(config, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
        
        print(f"✅ Configuration file created: {config}")
        print(f"📋 Organization: {org}")
        print(f"⚡ Max workers: {max_workers}")
        print(f"🔧 Jenkins-only mode: {'enabled' if jenkins_only else 'disabled'}")
        print(f"📝 Verbose logging: {'enabled' if verbose else 'disabled'}")
        if output:
            print(f"📄 JSON output: {output}")
        
        print("\n🎉 Setup complete! You can now run BuildCheck with:")
        print(f"   python build_check.py")
        print("\nOr with a custom config file:")
        print(f"   python build_check.py --config {config}")
        
        print("\n💡 To modify settings, edit the configuration file or use command line options.")
        print("   Command line options will override configuration file settings.")
        
    except Exception as e:
        print(f"❌ Error creating configuration file: {str(e)}")
        sys.exit(1)


@click.command()
@click.option('--config', default='config.yaml', help='Path to configuration file (default: config.yaml)')
def show_config(config: str):
    """
    Display current configuration settings
    """
    
    if not os.path.exists(config):
        print(f"❌ Configuration file not found: {config}")
        print("Run 'python setup_config.py' to create one.")
        return
    
    try:
        config_manager = ConfigManager(config)
        config_obj = config_manager.load_config()
        
        print(f"📋 Configuration: {config}")
        print(f"🏢 Organization: {config_obj.organization}")
        print(f"⚡ Max workers: {config_obj.parallelism.max_workers}")
        print(f"⏱️  Rate limit delay: {config_obj.parallelism.rate_limit_delay}s")
        print(f"🔧 Jenkins-only mode: {'enabled' if config_obj.analysis.jenkins_only else 'disabled'}")
        print(f"📝 Verbose logging: {'enabled' if config_obj.output.verbose else 'disabled'}")
        print(f"💾 Caching: {'enabled' if config_obj.caching.enabled else 'disabled'}")
        
        if config_obj.exclusions.repositories:
            print(f"🚫 Excluded repositories: {', '.join(config_obj.exclusions.repositories)}")
        if config_obj.exclusions.patterns:
            print(f"🚫 Exclusion patterns: {', '.join(config_obj.exclusions.patterns)}")
        
    except Exception as e:
        print(f"❌ Error reading configuration: {str(e)}")


@click.group()
def cli():
    """BuildCheck Configuration Management"""
    pass


cli.add_command(setup)
cli.add_command(show_config)


if __name__ == '__main__':
    cli() 