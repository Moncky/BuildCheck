#!/usr/bin/env python3
"""
Cache Manager for BuildCheck

This utility helps manage cache files for the BuildCheck tool.
It provides functions to list, clear, and inspect cache files.
"""

import os
import pickle
import click
import time
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()

def list_cache_files(cache_dir: str = ".cache"):
    """List all cache files with their details"""
    if not os.path.exists(cache_dir):
        console.print(f"[yellow]Cache directory '{cache_dir}' does not exist[/yellow]")
        return
    
    cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
    
    if not cache_files:
        console.print(f"[yellow]No cache files found in '{cache_dir}'[/yellow]")
        return
    
    table = Table(title=f"Cache Files in {cache_dir}")
    table.add_column("File", style="cyan")
    table.add_column("Organization", style="green")
    table.add_column("Type", style="magenta")
    table.add_column("Size", style="yellow")
    table.add_column("Age", style="blue")
    table.add_column("Repositories", style="red")
    
    for cache_file in sorted(cache_files):
        file_path = os.path.join(cache_dir, cache_file)
        file_size = os.path.getsize(file_path)
        file_age = time.time() - os.path.getmtime(file_path)
        
        # Parse filename to extract org and type
        parts = cache_file.replace('.pkl', '').split('_')
        if len(parts) >= 2:
            org_name = parts[0]
            cache_type = '_'.join(parts[1:])
        else:
            org_name = "unknown"
            cache_type = "unknown"
        
        # Try to load cache to get repository count
        try:
            with open(file_path, 'rb') as f:
                cached_data = pickle.load(f)
                repo_count = len(cached_data) if isinstance(cached_data, list) else "N/A"
        except Exception:
            repo_count = "Error"
        
        # Format age
        if file_age < 60:
            age_str = f"{file_age:.0f}s"
        elif file_age < 3600:
            age_str = f"{file_age/60:.0f}m"
        else:
            age_str = f"{file_age/3600:.1f}h"
        
        table.add_row(
            cache_file,
            org_name,
            cache_type,
            f"{file_size:,} bytes",
            age_str,
            str(repo_count)
        )
    
    console.print(table)

def clear_cache(cache_dir: str = ".cache", org: str = None):
    """Clear cache files"""
    if not os.path.exists(cache_dir):
        console.print(f"[yellow]Cache directory '{cache_dir}' does not exist[/yellow]")
        return
    
    cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
    
    if org:
        # Clear only files for specific organization
        cache_files = [f for f in cache_files if f.startswith(org.replace('/', '_').replace('\\', '_'))]
    
    if not cache_files:
        console.print(f"[yellow]No cache files to clear[/yellow]")
        return
    
    cleared_count = 0
    for cache_file in cache_files:
        try:
            file_path = os.path.join(cache_dir, cache_file)
            os.remove(file_path)
            console.print(f"[green]Cleared {cache_file}[/green]")
            cleared_count += 1
        except Exception as e:
            console.print(f"[red]Error clearing {cache_file}: {str(e)}[/red]")
    
    console.print(f"[green]Cleared {cleared_count} cache files[/green]")

def inspect_cache(cache_dir: str = ".cache", cache_file: str = None):
    """Inspect a specific cache file"""
    if not cache_file:
        console.print("[red]Please specify a cache file to inspect[/red]")
        return
    
    file_path = os.path.join(cache_dir, cache_file)
    if not os.path.exists(file_path):
        console.print(f"[red]Cache file '{cache_file}' not found[/red]")
        return
    
    try:
        with open(file_path, 'rb') as f:
            cached_data = pickle.load(f)
        
        console.print(f"[bold blue]Cache File: {cache_file}[/bold blue]")
        console.print(f"[blue]Size: {os.path.getsize(file_path):,} bytes[/blue]")
        console.print(f"[blue]Age: {time.time() - os.path.getmtime(file_path):.0f} seconds[/blue]")
        
        if isinstance(cached_data, list):
            console.print(f"[green]Contains {len(cached_data)} repositories:[/green]")
            for i, repo in enumerate(cached_data[:10]):  # Show first 10
                console.print(f"  {i+1}. {repo.name}")
            if len(cached_data) > 10:
                console.print(f"  ... and {len(cached_data) - 10} more")
        else:
            console.print(f"[yellow]Cache contains: {type(cached_data).__name__}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error reading cache file: {str(e)}[/red]")

@click.group()
def cli():
    """Cache Manager for BuildCheck"""
    pass

@cli.command()
@click.option('--cache-dir', default='.cache', help='Cache directory (default: .cache)')
def list(cache_dir):
    """List all cache files"""
    list_cache_files(cache_dir)

@cli.command()
@click.option('--cache-dir', default='.cache', help='Cache directory (default: .cache)')
@click.option('--org', help='Clear cache for specific organization only')
def clear(cache_dir, org):
    """Clear cache files"""
    if org:
        console.print(f"[bold red]Clearing cache for organization: {org}[/bold red]")
    else:
        console.print(f"[bold red]Clearing all cache files[/bold red]")
    clear_cache(cache_dir, org)

@cli.command()
@click.argument('cache_file')
@click.option('--cache-dir', default='.cache', help='Cache directory (default: .cache)')
def inspect(cache_file, cache_dir):
    """Inspect a specific cache file"""
    inspect_cache(cache_dir, cache_file)

if __name__ == '__main__':
    cli() 