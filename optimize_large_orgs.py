#!/usr/bin/env python3
"""
Optimized BuildCheck for Large Organizations

This script provides optimized analysis for large GitHub organizations
with 500+ repositories. It uses several techniques to minimize API calls:

1. Pagination with 100 repos per page (maximum allowed)
2. Bulk metadata fetching using search API
3. Aggressive caching
4. Reduced rate limiting delays
5. Smart repository filtering

Usage:
    python optimize_large_orgs.py --org your-org --optimized --use-cache
"""

import os
import sys
import time
from build_check import SimpleBuildAnalyzer, console

def analyze_large_organization(org_name: str, token: str, use_cache: bool = True):
    """
    Analyze a large organization with optimized settings
    
    Args:
        org_name: GitHub organization name
        token: GitHub personal access token
        use_cache: Whether to use caching
    """
    console.print(f"[bold blue]Starting optimized analysis of {org_name}[/bold blue]")
    console.print("[yellow]This mode is optimized for organizations with 500+ repositories[/yellow]")
    
    # Create analyzer with optimized settings for large organizations
    analyzer = SimpleBuildAnalyzer(
        github_token=token,
        org_name=org_name,
        rate_limit_delay=0.02,  # Faster rate limiting for large orgs
        max_workers=4,          # Reduced workers to avoid overwhelming API
        verbose=True,           # Enable verbose logging
        use_cache=use_cache,    # Always use cache for large orgs
        cache_dir=".cache"
    )
    
    # Check initial rate limit
    try:
        rate_limit = analyzer.github.get_rate_limit()
        console.print(f"[blue]Initial API calls remaining: {rate_limit.core.remaining}/{rate_limit.core.limit}[/blue]")
        
        if rate_limit.core.remaining < 1000:
            console.print("[red]Warning: Low API calls remaining. Consider running later.[/red]")
            return
    except Exception as e:
        console.print(f"[yellow]Could not check rate limit: {str(e)}[/yellow]")
    
    start_time = time.time()
    
    try:
        # Use optimized repository fetching
        console.print("[bold green]Using optimized repository fetching...[/bold green]")
        repos = analyzer.get_repositories_optimized()
        
        if not repos:
            console.print("[yellow]No repositories found to analyze[/yellow]")
            return
        
        console.print(f"[green]Found {len(repos)} repositories to analyze[/green]")
        
        # Analyze repositories with reduced parallelism
        console.print("[bold blue]Starting repository analysis...[/bold blue]")
        
        all_build_tools = []
        all_java_versions = []
        all_plugin_versions = []
        
        # Process repositories in smaller batches to avoid overwhelming the API
        batch_size = 50
        for i in range(0, len(repos), batch_size):
            batch = repos[i:i+batch_size]
            console.print(f"[blue]Processing batch {i//batch_size + 1}/{(len(repos) + batch_size - 1)//batch_size}[/blue]")
            
            for repo in batch:
                try:
                    build_tools, java_versions, plugin_versions = analyzer.analyze_repository(repo)
                    all_build_tools.extend(build_tools)
                    all_java_versions.extend(java_versions)
                    all_plugin_versions.extend(plugin_versions)
                except Exception as e:
                    console.print(f"[red]Error analyzing {repo.name}: {str(e)}[/red]")
            
            # Check rate limit after each batch
            try:
                rate_limit = analyzer.github.get_rate_limit()
                console.print(f"[blue]API calls remaining: {rate_limit.core.remaining}[/blue]")
                
                if rate_limit.core.remaining < 100:
                    console.print("[red]Rate limit approaching. Pausing...[/red]")
                    time.sleep(60)  # Wait 1 minute
            except Exception as e:
                console.print(f"[yellow]Could not check rate limit: {str(e)}[/yellow]")
        
        # Generate report
        console.print("[bold blue]Generating report...[/bold blue]")
        analyzer.generate_report(all_build_tools, all_java_versions, all_plugin_versions)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print(f"[green]Analysis completed in {total_time:.1f} seconds[/green]")
        console.print(f"[green]Total API calls made: {analyzer.api_calls_made}[/green]")
        
        # Final rate limit check
        try:
            final_rate_limit = analyzer.github.get_rate_limit()
            console.print(f"[blue]Final API calls remaining: {final_rate_limit.core.remaining}[/blue]")
        except Exception as e:
            console.print(f"[yellow]Could not check final rate limit: {str(e)}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error during analysis: {str(e)}[/red]")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimized BuildCheck for large organizations")
    parser.add_argument("--org", required=True, help="GitHub organization name")
    parser.add_argument("--token", envvar="GITHUB_TOKEN", help="GitHub personal access token")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    
    args = parser.parse_args()
    
    if not args.token:
        console.print("[red]GitHub token required. Set GITHUB_TOKEN environment variable or use --token[/red]")
        sys.exit(1)
    
    analyze_large_organization(
        org_name=args.org,
        token=args.token,
        use_cache=not args.no_cache
    ) 