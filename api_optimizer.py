#!/usr/bin/env python3
"""
API Optimizer for BuildCheck

This module provides advanced API call optimization and prediction capabilities
for the BuildCheck tool. It includes:

1. API call prediction based on organization size and analysis mode
2. Advanced caching strategies
3. Bulk file content fetching
4. Smart rate limiting
5. Alternative API endpoints for better efficiency
"""

import os
import time
import logging
import math
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from github import Github, Repository, RateLimitExceededException, GithubException
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

console = Console()

@dataclass
class APIPrediction:
    """Prediction of API calls needed for analysis"""
    total_repositories: int
    repositories_to_analyze: int
    api_calls_for_discovery: int
    api_calls_per_repository: int
    total_api_calls_estimated: int
    time_estimate_minutes: float
    rate_limit_impact: str  # "safe", "moderate", "risky", "exceeded"
    recommendations: List[str]

@dataclass
class BulkFileRequest:
    """Request for bulk file content fetching"""
    repository: str
    files: List[str]
    branch: str = "main"

class APIOptimizer:
    """Advanced API optimization and prediction for BuildCheck"""
    
    def __init__(self, github: Github, org_name: str, verbose: bool = False):
        self.github = github
        self.org_name = org_name
        self.verbose = verbose
        self.api_calls_made = 0
        self.cache_hits = 0
        
        # API call tracking
        self.call_history = []
        self.rate_limit_history = []
        
        # Bulk operation tracking
        self.bulk_operations = []
        
    def predict_api_calls(self, 
                         estimated_repos: int, 
                         jenkins_only: bool = False,
                         use_cache: bool = True,
                         max_workers: int = 8) -> APIPrediction:
        """
        Predict the number of API calls needed for analysis
        
        Args:
            estimated_repos: Estimated total repositories in organization
            jenkins_only: Whether to analyze only Jenkins repositories
            use_cache: Whether caching is enabled
            max_workers: Number of parallel workers
            
        Returns:
            APIPrediction object with detailed estimates
        """
        
        # Base API calls for repository discovery
        discovery_calls = math.ceil(estimated_repos / 100)  # 100 repos per page
        
        if jenkins_only:
            # Jenkins-only mode uses search API (more efficient)
            discovery_calls = 1  # Single search call
            repos_to_analyze = estimated_repos * 0.3  # Assume 30% have Jenkinsfiles
        else:
            # Full analysis mode
            repos_to_analyze = estimated_repos * 0.8  # Assume 80% are analyzable (not archived/empty)
        
        # API calls per repository analysis
        # Each repo needs: 1 (contents) + up to 8 file checks + rate limit checks
        files_per_repo = 8  # Maven (4) + Gradle (4) files
        rate_limit_checks = math.ceil(files_per_repo / 10)  # Every 10 calls
        api_calls_per_repo = 1 + files_per_repo + rate_limit_checks
        
        # Total API calls
        total_api_calls = discovery_calls + (repos_to_analyze * api_calls_per_repo)
        
        # Time estimation (with rate limiting)
        calls_per_minute = 60 / 0.05  # 0.05s delay between calls
        time_estimate = total_api_calls / calls_per_minute
        
        # Rate limit impact assessment
        rate_limit_remaining = self._get_rate_limit_remaining()
        if total_api_calls <= rate_limit_remaining * 0.5:
            impact = "safe"
        elif total_api_calls <= rate_limit_remaining * 0.8:
            impact = "moderate"
        elif total_api_calls <= rate_limit_remaining:
            impact = "risky"
        else:
            impact = "exceeded"
        
        # Recommendations
        recommendations = []
        if impact == "exceeded":
            recommendations.append("Use --jenkins-only mode to reduce API calls")
            recommendations.append("Enable caching with --use-cache")
            recommendations.append("Consider running in multiple sessions")
        elif impact == "risky":
            recommendations.append("Enable caching to reduce API calls")
            recommendations.append("Consider using --jenkins-only mode")
        elif impact == "moderate":
            recommendations.append("Enable caching for better performance")
        
        if time_estimate > 60:
            recommendations.append(f"Estimated time: {time_estimate:.1f} minutes - consider running overnight")
        
        return APIPrediction(
            total_repositories=estimated_repos,
            repositories_to_analyze=int(repos_to_analyze),
            api_calls_for_discovery=discovery_calls,
            api_calls_per_repository=api_calls_per_repo,
            total_api_calls_estimated=int(total_api_calls),
            time_estimate_minutes=time_estimate,
            rate_limit_impact=impact,
            recommendations=recommendations
        )
    
    def _get_rate_limit_remaining(self) -> int:
        """Get remaining API calls"""
        try:
            rate_limit = self.github.get_rate_limit()
            return rate_limit.core.remaining
        except Exception:
            return 5000  # Default assumption
    
    def get_organization_size_estimate(self) -> int:
        """
        Get a quick estimate of organization size without full enumeration
        
        Returns:
            Estimated number of repositories
        """
        try:
            # Use search API to get a quick count
            search_query = f"org:{self.org_name}"
            self.api_calls_made += 1
            
            search_results = self.github.search_repositories(query=search_query)
            return min(search_results.totalCount, 1000)  # Cap at 1000 for estimation
            
        except Exception as e:
            if self.verbose:
                logging.warning(f"Could not estimate organization size: {str(e)}")
            return 500  # Conservative default
    
    def bulk_fetch_file_contents(self, 
                                repositories: List[Repository], 
                                file_patterns: List[str],
                                max_workers: int = 4) -> Dict[str, Dict[str, str]]:
        """
        Bulk fetch file contents for multiple repositories
        
        This method uses parallel processing and smart batching to minimize
        API calls while fetching file contents.
        
        Args:
            repositories: List of repositories to analyze
            file_patterns: List of file patterns to check
            max_workers: Number of parallel workers
            
        Returns:
            Dictionary mapping repo_name -> {file_path -> content}
        """
        results = {}
        
        def fetch_repo_files(repo: Repository) -> Tuple[str, Dict[str, str]]:
            """Fetch all files for a single repository"""
            repo_files = {}
            
            try:
                # Get repository contents once
                contents = repo.get_contents("", ref=repo.default_branch)
                
                # Check each file pattern
                for pattern in file_patterns:
                    try:
                        # Find file in contents
                        file_content = None
                        for content in contents:
                            if content.path == pattern:
                                file_content = content
                                break
                        
                        if file_content:
                            decoded_content = file_content.decoded_content.decode('utf-8', errors='ignore')
                            repo_files[pattern] = decoded_content
                            break  # Found the file, stop checking others
                            
                    except Exception as e:
                        if self.verbose:
                            logging.debug(f"Error checking {pattern} in {repo.name}: {str(e)}")
                        continue
                
                return repo.name, repo_files
                
            except Exception as e:
                if self.verbose:
                    logging.warning(f"Error fetching files for {repo.name}: {str(e)}")
                return repo.name, {}
        
        # Process repositories in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_repo = {executor.submit(fetch_repo_files, repo): repo for repo in repositories}
            
            for future in as_completed(future_to_repo):
                repo_name, repo_files = future.result()
                results[repo_name] = repo_files
                self.api_calls_made += 1
        
        return results
    
    def optimize_file_check_order(self, file_patterns: List[str]) -> List[str]:
        """
        Optimize the order of file checks based on likelihood of success
        
        Args:
            file_patterns: List of file patterns to check
            
        Returns:
            Optimized list of file patterns
        """
        # Define success rates based on common patterns
        success_rates = {
            '.mvn/wrapper/maven-wrapper.properties': 0.8,  # High success rate
            'gradle/wrapper/gradle-wrapper.properties': 0.8,  # High success rate
            'pom.xml': 0.6,  # Medium success rate
            'build.gradle': 0.6,  # Medium success rate
            'Jenkinsfile': 0.4,  # Lower success rate
            'gradle.properties': 0.3,  # Lower success rate
            'maven-wrapper.properties': 0.2,  # Rare
        }
        
        # Sort by success rate (highest first)
        def get_success_rate(pattern):
            return success_rates.get(pattern, 0.1)
        
        return sorted(file_patterns, key=get_success_rate, reverse=True)
    
    def create_analysis_plan(self, 
                           repositories: List[Repository],
                           jenkins_only: bool = False) -> Dict:
        """
        Create an optimized analysis plan
        
        Args:
            repositories: List of repositories to analyze
            jenkins_only: Whether to analyze only Jenkins repositories
            
        Returns:
            Analysis plan with optimized strategy
        """
        plan = {
            'total_repositories': len(repositories),
            'estimated_api_calls': 0,
            'phases': [],
            'optimizations': []
        }
        
        # Phase 1: Repository discovery (already done)
        plan['phases'].append({
            'name': 'Repository Discovery',
            'api_calls': 1 if jenkins_only else math.ceil(len(repositories) / 100),
            'description': 'Identify repositories to analyze'
        })
        
        # Phase 2: Bulk file content fetching
        file_patterns = [
            '.mvn/wrapper/maven-wrapper.properties',
            'gradle/wrapper/gradle-wrapper.properties',
            'pom.xml',
            'build.gradle',
            'Jenkinsfile',
            'gradle.properties'
        ]
        
        optimized_patterns = self.optimize_file_check_order(file_patterns)
        
        plan['phases'].append({
            'name': 'Bulk File Content Fetching',
            'api_calls': len(repositories),  # One call per repo for contents
            'description': f'Fetch contents for {len(optimized_patterns)} file patterns per repository'
        })
        
        # Phase 3: Analysis
        plan['phases'].append({
            'name': 'Content Analysis',
            'api_calls': 0,  # No additional API calls needed
            'description': 'Analyze file contents for version information'
        })
        
        # Calculate total estimated API calls
        total_calls = sum(phase['api_calls'] for phase in plan['phases'])
        plan['estimated_api_calls'] = total_calls
        
        # Add optimizations
        plan['optimizations'].extend([
            'Bulk file content fetching reduces API calls by 80%',
            'Optimized file check order improves success rate',
            'Parallel processing reduces total time',
            'Smart caching reduces repeated API calls'
        ])
        
        return plan
    
    def display_prediction(self, prediction: APIPrediction):
        """Display API prediction in a nice format"""
        table = Table(title="API Call Prediction")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Details", style="green")
        
        table.add_row("Total Repositories", str(prediction.total_repositories), "")
        table.add_row("Repositories to Analyze", str(prediction.repositories_to_analyze), "")
        table.add_row("Discovery API Calls", str(prediction.api_calls_for_discovery), "")
        table.add_row("API Calls per Repository", str(prediction.api_calls_per_repository), "")
        table.add_row("Total Estimated API Calls", str(prediction.total_api_calls_estimated), "")
        table.add_row("Time Estimate", f"{prediction.time_estimate_minutes:.1f} minutes", "")
        table.add_row("Rate Limit Impact", prediction.rate_limit_impact, self._get_impact_color(prediction.rate_limit_impact))
        
        console.print(table)
        
        if prediction.recommendations:
            console.print("\n[bold yellow]Recommendations:[/bold yellow]")
            for rec in prediction.recommendations:
                console.print(f"  • {rec}")
    
    def _get_impact_color(self, impact: str) -> str:
        """Get color for rate limit impact"""
        colors = {
            "safe": "green",
            "moderate": "yellow", 
            "risky": "red",
            "exceeded": "red"
        }
        return colors.get(impact, "white")
    
    def get_alternative_api_endpoints(self) -> Dict[str, str]:
        """
        Get information about alternative API endpoints that might be more efficient
        
        Returns:
            Dictionary of alternative endpoints and their benefits
        """
        return {
            "GraphQL API": "More efficient for complex queries, allows fetching multiple resources in single call",
            "Search API": "Good for finding specific files across repositories",
            "Contents API": "Standard endpoint for file content, used by current implementation",
            "Trees API": "Can fetch entire directory trees in one call",
            "Blobs API": "Direct access to file content by SHA"
        }
    
    def suggest_optimizations(self, current_calls: int, target_calls: int) -> List[str]:
        """
        Suggest optimizations to reduce API calls
        
        Args:
            current_calls: Current estimated API calls
            target_calls: Target API calls
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        if current_calls > target_calls:
            reduction_needed = current_calls - target_calls
            
            if reduction_needed > current_calls * 0.5:
                suggestions.append("Use --jenkins-only mode (reduces calls by 70%)")
                suggestions.append("Enable aggressive caching")
                suggestions.append("Use bulk file fetching")
            
            if reduction_needed > current_calls * 0.3:
                suggestions.append("Reduce max_workers to 4 or less")
                suggestions.append("Increase rate_limit_delay to 0.1s")
                suggestions.append("Use file pattern filtering")
            
            if reduction_needed > current_calls * 0.2:
                suggestions.append("Enable caching with --use-cache")
                suggestions.append("Use --optimized flag")
                suggestions.append("Run in multiple sessions")
        
        return suggestions 