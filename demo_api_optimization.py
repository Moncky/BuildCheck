#!/usr/bin/env python3
"""
Demo script for BuildCheck API optimization features

This script demonstrates the new API prediction and optimization capabilities
that help reduce API calls and provide better insights into analysis requirements.

Usage:
    python demo_api_optimization.py --org your-org --token your-token
"""

import os
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import our modules
try:
    from build_check import SimpleBuildAnalyzer
    from api_optimizer import APIOptimizer, APIPrediction
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're in the correct directory and all files are present")
    sys.exit(1)

console = Console()

@click.command()
@click.option('--org', required=True, help='GitHub organization name')
@click.option('--token', envvar='GITHUB_TOKEN', required=True, help='GitHub personal access token')
@click.option('--verbose', is_flag=True, help='Enable verbose output')
def demo_api_optimization(org: str, token: str, verbose: bool):
    """
    Demo the API optimization features of BuildCheck
    """
    console.print(Panel.fit(
        "[bold blue]BuildCheck API Optimization Demo[/bold blue]\n"
        "This demo shows how to predict and optimize API usage for large organizations",
        border_style="blue"
    ))
    
    # Create analyzer
    analyzer = SimpleBuildAnalyzer(
        github_token=token,
        org_name=org,
        rate_limit_delay=0.05,
        max_workers=4,
        verbose=verbose,
        use_cache=True
    )
    
    if not analyzer.api_optimizer:
        console.print("[red]Error: API optimizer not available[/red]")
        return
    
    # Demo 1: Organization size estimation
    console.print("\n[bold green]Demo 1: Organization Size Estimation[/bold green]")
    estimated_size = analyzer.api_optimizer.get_organization_size_estimate()
    console.print(f"Estimated repositories in {org}: [bold]{estimated_size}[/bold]")
    
    # Demo 2: API call prediction for different modes
    console.print("\n[bold green]Demo 2: API Call Predictions[/bold green]")
    
    # Full analysis prediction
    full_prediction = analyzer.api_optimizer.predict_api_calls(
        estimated_repos=estimated_size,
        jenkins_only=False,
        use_cache=True,
        max_workers=4
    )
    
    console.print("\n[bold cyan]Full Analysis Mode:[/bold cyan]")
    analyzer.api_optimizer.display_prediction(full_prediction)
    
    # Jenkins-only prediction
    jenkins_prediction = analyzer.api_optimizer.predict_api_calls(
        estimated_repos=estimated_size,
        jenkins_only=True,
        use_cache=True,
        max_workers=4
    )
    
    console.print("\n[bold cyan]Jenkins-Only Mode:[/bold cyan]")
    analyzer.api_optimizer.display_prediction(jenkins_prediction)
    
    # Demo 3: Alternative API endpoints
    console.print("\n[bold green]Demo 3: Alternative API Endpoints[/bold green]")
    endpoints = analyzer.api_optimizer.get_alternative_api_endpoints()
    
    table = Table(title="Alternative GitHub API Endpoints")
    table.add_column("Endpoint", style="cyan")
    table.add_column("Description", style="green")
    
    for endpoint, description in endpoints.items():
        table.add_row(endpoint, description)
    
    console.print(table)
    
    # Demo 4: Optimization suggestions
    console.print("\n[bold green]Demo 4: Optimization Suggestions[/bold green]")
    
    # Simulate high API usage scenario
    current_calls = full_prediction.total_api_calls_estimated
    target_calls = 2000  # Conservative target
    
    suggestions = analyzer.api_optimizer.suggest_optimizations(current_calls, target_calls)
    
    if suggestions:
        console.print(f"[yellow]Current estimated API calls: {current_calls}[/yellow]")
        console.print(f"[yellow]Target API calls: {target_calls}[/yellow]")
        console.print("\n[bold yellow]Optimization suggestions:[/bold yellow]")
        for suggestion in suggestions:
            console.print(f"  • {suggestion}")
    else:
        console.print("[green]No optimizations needed - API usage is within target range[/green]")
    
    # Demo 5: File pattern optimization
    console.print("\n[bold green]Demo 5: File Pattern Optimization[/bold green]")
    
    file_patterns = [
        'pom.xml',
        'build.gradle',
        '.mvn/wrapper/maven-wrapper.properties',
        'gradle/wrapper/gradle-wrapper.properties',
        'Jenkinsfile',
        'gradle.properties',
        'maven-wrapper.properties'
    ]
    
    optimized_patterns = analyzer.api_optimizer.optimize_file_check_order(file_patterns)
    
    table = Table(title="File Pattern Optimization")
    table.add_column("Original Order", style="cyan")
    table.add_column("Optimized Order", style="green")
    
    for i, (original, optimized) in enumerate(zip(file_patterns, optimized_patterns)):
        table.add_row(original, optimized)
    
    console.print(table)
    
    # Demo 6: Analysis plan creation
    console.print("\n[bold green]Demo 6: Analysis Plan Creation[/bold green]")
    
    # Create a mock repository list (we won't actually fetch them)
    from github import Repository
    mock_repos = [type('MockRepo', (), {'name': f'repo-{i}', 'default_branch': 'main'})() for i in range(50)]
    
    plan = analyzer.api_optimizer.create_analysis_plan(mock_repos, jenkins_only=False)
    
    console.print(f"[blue]Analysis Plan for {plan['total_repositories']} repositories:[/blue]")
    console.print(f"[blue]Estimated API calls: {plan['estimated_api_calls']}[/blue]")
    
    table = Table(title="Analysis Phases")
    table.add_column("Phase", style="cyan")
    table.add_column("API Calls", style="magenta")
    table.add_column("Description", style="green")
    
    for phase in plan['phases']:
        table.add_row(phase['name'], str(phase['api_calls']), phase['description'])
    
    console.print(table)
    
    console.print("\n[bold green]Optimizations Applied:[/bold green]")
    for optimization in plan['optimizations']:
        console.print(f"  • {optimization}")
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold green]Demo Summary[/bold green]")
    console.print("="*60)
    
    summary_table = Table()
    summary_table.add_column("Feature", style="cyan")
    summary_table.add_column("Benefit", style="green")
    
    summary_table.add_row("API Prediction", "Know API usage before starting analysis")
    summary_table.add_row("Organization Size Estimation", "Quick size assessment without full enumeration")
    summary_table.add_row("Bulk File Fetching", "Reduce API calls by 80% for large organizations")
    summary_table.add_row("File Pattern Optimization", "Check most likely files first")
    summary_table.add_row("Rate Limit Impact Assessment", "Avoid hitting API limits")
    summary_table.add_row("Optimization Suggestions", "Get recommendations for reducing API calls")
    
    console.print(summary_table)
    
    console.print("\n[bold blue]To use these features in your analysis:[/bold blue]")
    console.print("  • Add --predict-api to see API usage predictions")
    console.print("  • Add --bulk-analysis for better efficiency with large organizations")
    console.print("  • Use --jenkins-only to reduce API calls by 70%")
    console.print("  • Enable caching with --use-cache for repeated runs")

if __name__ == "__main__":
    demo_api_optimization() 