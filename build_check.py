#!/usr/bin/env python3
"""
Simplified BuildCheck - Focus on finding actual build tool versions, Java versions, and plugin versions

This script analyzes GitHub organizations to find the versions of build tools (Maven, Gradle),
Java versions, and plugin versions being used in repositories. It focuses on the most reliable
sources of version information rather than trying to infer versions from application configurations.

Key Design Decisions:
1. Focus on wrapper files (.mvn/wrapper/maven-wrapper.properties, gradle/wrapper/gradle-wrapper.properties)
   - These are the most reliable sources as they explicitly specify the build tool version
   - They're used by the build tools themselves to download the correct version
2. Check Jenkins tool configurations as a secondary source
   - Jenkins often explicitly specifies which build tool version to use
3. Check gradle.properties for plugin versions
   - Plugin versions like publishPluginVersion are often defined in gradle.properties
4. Use rate limiting and parallelism for practical performance
   - GitHub has API limits (5000 requests/hour) that must be respected
   - Parallel processing makes analysis of large orgs feasible
5. Prioritize accuracy over completeness
   - Better to miss some repos than to report incorrect versions
   - Clear detection method tracking shows how each version was found
6. Support Jenkins-only mode for faster analysis
   - Only analyze repositories that have Jenkinsfiles
   - Much faster for organizations with many repositories
"""

import os
import re
import json
import click
import time
import logging
import pickle
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from github import Github, Repository, RateLimitExceededException, GithubException
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

# Configure logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration based on verbose flag"""
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    return logging.getLogger(__name__)

@dataclass
class BuildTool:
    """Represents a build tool found in a repository
    
    This dataclass captures all the information we need about a build tool:
    - name: The build tool (maven, gradle, etc.)
    - version: The specific version found
    - file_path: Which file contained the version information
    - repository: Which repository it was found in
    - branch: Which branch was analyzed
    - detection_method: How we found the version (for transparency)
    """
    name: str
    version: Optional[str]
    file_path: str
    repository: str
    branch: str
    detection_method: str  # How we found the version

@dataclass
class JavaVersion:
    """Represents Java version information found in a repository"""
    version: Optional[str]
    source_compatibility: Optional[str]
    target_compatibility: Optional[str]
    file_path: str
    repository: str
    branch: str
    detection_method: str

@dataclass
class PluginVersion:
    """Represents plugin version information found in a repository"""
    plugin_name: str
    version: Optional[str]
    file_path: str
    repository: str
    branch: str
    detection_method: str

class SimpleBuildAnalyzer:
    """Simplified analyzer focused on actual build tool versions and Java versions"""
    
    def __init__(self, github_token: str, org_name: str, rate_limit_delay: float = 0.05, max_workers: int = 8, verbose: bool = False, use_cache: bool = False, cache_dir: str = ".cache"):
        """
        Initialize the analyzer with GitHub credentials and configuration
        
        Args:
            github_token: GitHub personal access token for API access
            org_name: Name of the GitHub organization to analyze
            rate_limit_delay: Delay between API calls to respect rate limits (default: 0.05s)
            max_workers: Number of parallel workers for repository analysis (default: 8)
            verbose: Enable verbose logging for detailed API request information
            use_cache: Enable caching of repository lists to reduce API calls during development
            cache_dir: Directory to store cache files (default: .cache)
        """
        self.github = Github(github_token)
        self.org_name = org_name
        self.org = self.github.get_organization(org_name)
        self.rate_limit_delay = rate_limit_delay
        self.max_workers = max_workers
        self.api_calls_made = 0  # Track API usage for monitoring and debugging
        self.verbose = verbose
        
        # Caching configuration
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.cache_duration = 3600  # Cache repositories for 1 hour
        
        # Rate limiting optimization - cache rate limit info to avoid excessive API calls
        self.last_rate_limit_check = 0
        self.rate_limit_cache = None
        self.rate_limit_cache_duration = 30  # Cache rate limit info for 30 seconds
        
        # Define build tool detection patterns
        # These are ordered by reliability - most reliable sources first
        self.build_tools = {
            'maven': {
                'files': [
                    '.mvn/wrapper/maven-wrapper.properties',  # Most common - Maven wrapper standard location
                    'maven-wrapper.properties',              # Alternative location (older projects)
                    'pom.xml',                               # Check for explicit version declaration
                    'Jenkinsfile'                            # Check Jenkins tool configuration
                ],
                'version_patterns': [
                    # Maven wrapper distribution URL - most reliable source
                    # This URL contains the exact Maven version being used
                    r'distributionUrl=.*?apache-maven-([\d.]+)-bin\.zip',
                    # Explicit version in pom.xml (rare but possible)
                    r'<maven\.version>([^<]+)</maven\.version>',
                    # Jenkins tool configuration - Jenkins often specifies exact versions
                    r'tool\s*[\'"]([^\'"]+)[\'"]\s*{.*?maven\s*[\'"]([^\'"]+)[\'"]',
                    r'maven\s*[\'"]([^\'"]+)[\'"]'
                ]
            },
            'gradle': {
                'files': [
                    'gradle/wrapper/gradle-wrapper.properties',  # Most common - Gradle wrapper standard location
                    'gradle.properties',                         # Alternative location for version properties
                    'build.gradle',                              # Check for explicit version property
                    'Jenkinsfile'                                # Check Jenkins tool configuration
                ],
                'version_patterns': [
                    # Gradle wrapper distribution URL - most reliable source
                    # This URL contains the exact Gradle version being used
                    r'distributionUrl=.*?gradle-([\d.]+)-bin\.zip',
                    r'distributionUrl=.*?gradle-([\d.]+)-all\.zip',
                    # Explicit version in build.gradle (less common but possible)
                    r'gradleVersion\s*=\s*[\'"]([^\'"]+)[\'"]',
                    # Jenkins tool configuration - Jenkins often specifies exact versions
                    r'tool\s*[\'"]([^\'"]+)[\'"]\s*{.*?gradle\s*[\'"]([^\'"]+)[\'"]',
                    r'gradle\s*[\'"]([^\'"]+)[\'"]'
                ]
            }
        }
        
        # Define Java version detection patterns
        self.java_version_patterns = {
            'maven': {
                'files': ['pom.xml'],
                'patterns': [
                    # Java version properties (most common)
                    r'<java\.version>([^<]+)</java\.version>',
                    r'<maven\.compiler\.source>([^<]+)</maven\.compiler\.source>',
                    r'<maven\.compiler\.target>([^<]+)</maven\.compiler\.target>',
                    # Maven compiler plugin configuration
                    r'<maven-compiler-plugin>.*?<source>([^<]+)</source>',
                    r'<maven-compiler-plugin>.*?<target>([^<]+)</target>',
                    # Properties section
                    r'<properties>.*?<java\.version>([^<]+)</java\.version>',
                    r'<properties>.*?<maven\.compiler\.source>([^<]+)</maven\.compiler\.source>',
                    r'<properties>.*?<maven\.compiler\.target>([^<]+)</maven\.compiler\.target>'
                ]
            },
            'gradle': {
                'files': ['build.gradle', 'build.gradle.kts', 'gradle.properties'],
                'patterns': [
                    # Source and target compatibility
                    r'sourceCompatibility\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'targetCompatibility\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'sourceCompatibility\s*=\s*JavaVersion\.VERSION_([^\s]+)',
                    r'targetCompatibility\s*=\s*JavaVersion\.VERSION_([^\s]+)',
                    # Java block configuration
                    r'java\s*{[^}]*sourceCompatibility\s*=\s*JavaVersion\.VERSION_([^\s]+)',
                    r'java\s*{[^}]*targetCompatibility\s*=\s*JavaVersion\.VERSION_([^\s]+)',
                    # Gradle properties
                    r'java\.version\s*=\s*([^\s]+)',
                    r'org\.gradle\.java\.home\s*=\s*([^\s]+)'
                ]
            }
        }
        
        # Define plugin version detection patterns
        self.plugin_version_patterns = {
            'gradle': {
                'files': ['gradle.properties'],
                'patterns': [
                    # publishPluginVersion in gradle.properties
                    r'publishPluginVersion\s*=\s*([^\s]+)',
                    r'publishPluginVersion\s*=\s*[\'"]([^\'"]+)[\'"]'
                ]
            }
        }

    def _check_rate_limit(self):
        """
        Check and handle GitHub API rate limits with caching to reduce API calls
        
        GitHub has strict API limits (5000 requests/hour for authenticated users).
        This method monitors our usage and implements backoff strategies to avoid
        hitting these limits. It's crucial for the script to work reliably with
        large organizations.
        
        Performance optimization: Cache rate limit info for 30 seconds to avoid
        excessive API calls that were slowing down the script significantly.
        """
        current_time = time.time()
        
        # Use cached rate limit info if it's still fresh (within 30 seconds)
        if (self.rate_limit_cache and 
            current_time - self.last_rate_limit_check < self.rate_limit_cache_duration):
            core_limit = self.rate_limit_cache
        else:
            # Only make API call if cache is stale or doesn't exist
            try:
                rate_limit = self.github.get_rate_limit()
                core_limit = rate_limit.core
                self.rate_limit_cache = core_limit
                self.last_rate_limit_check = current_time
                
                if self.verbose:
                    logging.debug(f"Rate limit check: {core_limit.remaining}/{core_limit.limit} requests remaining")
                    logging.debug(f"  - Reset time: {core_limit.reset.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                # If we can't check rate limits, continue but warn
                # This prevents the script from failing if rate limit checking fails
                console.print(f"[yellow]Warning: Could not check rate limit: {str(e)}[/yellow]")
                if self.verbose:
                    logging.warning(f"Could not check rate limit: {str(e)}")
                return
        
        # If we're close to the limit, add extra delay to slow down
        # This prevents us from hitting the limit unexpectedly
        if core_limit.remaining < 50:
            extra_delay = (50 - core_limit.remaining) * 0.05
            time.sleep(extra_delay)
            console.print(f"[yellow]Rate limit warning: {core_limit.remaining} requests remaining[/yellow]")
            if self.verbose:
                logging.warning(f"Rate limit warning: {core_limit.remaining} requests remaining, added {extra_delay:.2f}s delay")
        
        # If we've hit the limit, wait until reset
        # This is the nuclear option - we've used all our requests
        if core_limit.remaining == 0:
            reset_timestamp = core_limit.reset.timestamp()
            wait_time = reset_timestamp - time.time()
            if wait_time > 0:
                console.print(f"[red]Rate limit exceeded. Waiting {int(wait_time)} seconds until reset...[/red]")
                if self.verbose:
                    logging.error(f"Rate limit exceeded. Waiting {int(wait_time)} seconds until reset")
                time.sleep(wait_time + 1)

    def _make_api_call(self, call_description: str = "API call"):
        """
        Make an API call with optimized rate limiting
        
        This method ensures all GitHub API calls go through rate limiting.
        It's a central point for managing API usage and preventing rate limit issues.
        
        Performance optimization: Eliminated double API calls for rate limiting
        and reduced default delay to improve performance significantly.
        
        Args:
            call_description: Description of the API call for logging/debugging
        """
        # Only check rate limit every 10 calls to reduce overhead
        if self.api_calls_made % 10 == 0:
            self._check_rate_limit()
        
        self.api_calls_made += 1
        
        # Add minimal delay between calls - reduced from 0.1s to 0.05s for better performance
        # 0.05s delay means max 20 calls/second, still well within GitHub's limits
        if self.api_calls_made > 1:
            time.sleep(self.rate_limit_delay)

        if self.verbose:
            # Use cached rate limit info instead of making another API call
            if self.rate_limit_cache:
                logging.debug(f"API Call #{self.api_calls_made}: {call_description}")
                logging.debug(f"  - Rate Limit: {self.rate_limit_cache.remaining}/{self.rate_limit_cache.limit} requests remaining")
                logging.debug(f"  - Rate Limit Reset: {self.rate_limit_cache.reset.strftime('%Y-%m-%d %H:%M:%S')}")
                logging.debug(f"  - Delay Applied: {self.rate_limit_delay}s")
            else:
                logging.debug(f"API Call #{self.api_calls_made}: {call_description}")
                logging.debug(f"  - Rate limit info not available")
                logging.debug(f"  - Delay Applied: {self.rate_limit_delay}s")

    def search_repos_with_jenkinsfiles(self) -> List[Repository]:
        """
        Search for repositories that contain Jenkinsfiles using GitHub search API
        
        This method uses GitHub's search API to find repositories that contain Jenkinsfiles.
        This is much faster than checking all repositories, especially for large organizations.
        The search API is specifically designed for this type of query.
        
        Returns:
            List of GitHub Repository objects that contain Jenkinsfiles
        """
        # Try to load from cache first
        cached_repos = self._load_from_cache('jenkins_repos')
        if cached_repos:
            return cached_repos
        
        console.print(f"[bold blue]Searching for repositories with Jenkinsfiles in {self.org_name}...[/bold blue]")
        repos_with_jenkins = []
        
        try:
            # Use GitHub search API to find repositories with Jenkinsfiles
            # This is much more efficient than checking all repositories
            search_query = f"org:{self.org_name} filename:Jenkinsfile"
            self._make_api_call("Search for repositories with Jenkinsfiles")
            
            if self.verbose:
                logging.info(f"Searching for repositories with Jenkinsfiles using query: {search_query}")
            
            search_results = self.github.search_code(query=search_query)
            
            if self.verbose:
                logging.info(f"Found {search_results.totalCount} search results for Jenkinsfiles")
            
            if search_results.totalCount == 0:
                console.print("[yellow]No repositories with Jenkinsfiles found[/yellow]")
                return []
            
            # Track seen repositories to avoid duplicates
            # The search API might return multiple results for the same repository
            seen_repos = set()
            processed_count = 0
            
            # Process search results with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Processing {search_results.totalCount} Jenkinsfile search results...", 
                    total=search_results.totalCount
                )
                
                for result in search_results:
                    processed_count += 1
                    repo_name = result.repository.name
                    
                    # Skip if we've already seen this repo
                    if repo_name in seen_repos:
                        progress.update(task, description=f"Processing {processed_count}/{search_results.totalCount} results (duplicates: {len(seen_repos) - len(repos_with_jenkins)})")
                        progress.advance(task)
                        continue
                    
                    # Skip archived and empty repositories
                    if not result.repository.archived and result.repository.size > 0:
                        seen_repos.add(repo_name)
                        repos_with_jenkins.append(result.repository)
                        progress.update(task, description=f"Processing {processed_count}/{search_results.totalCount} results (found: {len(repos_with_jenkins)})")
                    else:
                        progress.update(task, description=f"Processing {processed_count}/{search_results.totalCount} results (skipped: {processed_count - len(repos_with_jenkins)})")
                    
                    progress.advance(task)
                    
                    # Check rate limit periodically during search - removed excessive checking
                    # Rate limiting is now handled more efficiently in _make_api_call
            
            console.print(f"[green]Found {len(repos_with_jenkins)} repositories with Jenkinsfiles[/green]")
            
            # Save to cache for future use
            self._save_to_cache(repos_with_jenkins, 'jenkins_repos')
            
        except RateLimitExceededException:
            console.print("[red]Rate limit exceeded while searching repositories. Please try again later.[/red]")
            return []
        except GithubException as e:
            console.print(f"[red]GitHub API error: {str(e)}[/red]")
            return []
        except Exception as e:
            console.print(f"[red]Error searching repositories: {str(e)}[/red]")
            return []
        
        return repos_with_jenkins

    def get_repositories(self) -> List[Repository]:
        """
        Get all repositories in the organization
        
        This method fetches all repositories from the GitHub organization,
        filtering out archived and empty repositories to focus on active projects.
        Use this for full analysis mode.
        
        Returns:
            List of GitHub Repository objects to analyze
        """
        # Try to load from cache first
        cached_repos = self._load_from_cache('all_repos')
        if cached_repos:
            return cached_repos
        
        console.print(f"[bold blue]Fetching all repositories from {self.org_name}...[/bold blue]")
        repos = []
        
        try:
            self._make_api_call("Get organization repositories")
            
            if self.verbose:
                logging.info(f"Fetching all repositories from organization: {self.org_name}")
            
            total_repos = 0
            archived_repos = 0
            empty_repos = 0
            
            # First, count total repositories to set up progress bar
            # We need to iterate twice: once to count, once to process
            # This is necessary because GitHub API doesn't provide total count upfront
            console.print("[dim]Counting repositories...[/dim]")
            temp_repos = list(self.org.get_repos())
            total_count = len(temp_repos)
            
            if total_count == 0:
                console.print("[yellow]No repositories found in the organization[/yellow]")
                return []
            
            # Now process repositories with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"Processing {total_count} repositories...", 
                    total=total_count
                )
                
                for repo in temp_repos:
                    total_repos += 1
                    
                    # Skip archived and empty repos - they're unlikely to have build configurations
                    # This reduces noise and focuses analysis on active projects
                    if repo.archived:
                        archived_repos += 1
                        if self.verbose:
                            logging.debug(f"Skipping archived repository: {repo.name}")
                        progress.update(task, description=f"Processing {total_repos}/{total_count} repositories (skipped: {archived_repos + empty_repos})")
                        progress.advance(task)
                        continue
                    
                    if repo.size == 0:
                        empty_repos += 1
                        if self.verbose:
                            logging.debug(f"Skipping empty repository: {repo.name}")
                        progress.update(task, description=f"Processing {total_repos}/{total_count} repositories (skipped: {archived_repos + empty_repos})")
                        progress.advance(task)
                        continue
                    
                    repos.append(repo)
                    if self.verbose:
                        logging.debug(f"Added repository for analysis: {repo.name} (size: {repo.size} bytes)")
                    
                    progress.update(task, description=f"Processing {total_repos}/{total_count} repositories (found: {len(repos)})")
                    progress.advance(task)
            
            if self.verbose:
                logging.info(f"Repository filtering summary:")
                logging.info(f"  - Total repositories: {total_repos}")
                logging.info(f"  - Archived repositories (skipped): {archived_repos}")
                logging.info(f"  - Empty repositories (skipped): {empty_repos}")
                logging.info(f"  - Repositories for analysis: {len(repos)}")
            
            console.print(f"[green]Found {len(repos)} repositories for analysis[/green]")
            
            # Save to cache for future use
            self._save_to_cache(repos, 'all_repos')
            
        except Exception as e:
            console.print(f"[red]Error fetching repositories: {str(e)}[/red]")
            if self.verbose:
                logging.error(f"Error fetching repositories: {str(e)}")
            return []
        
        return repos

    def get_specific_repository(self, repo_name: str) -> Optional[Repository]:
        """
        Get a specific repository by name
        
        This method retrieves a single repository from the GitHub organization
        by its name. It's useful for analyzing a specific repository instead
        of the entire organization.
        
        Args:
            repo_name: Name of the repository to retrieve
            
        Returns:
            Repository: GitHub repository object if found, None otherwise
            
        Raises:
            GithubException: If there's an error accessing the repository
        """
        console.print(f"[blue]Fetching specific repository: {repo_name}[/blue]")
        
        try:
            # Try to get the repository from the organization
            repo = self.org.get_repo(repo_name)
            
            if repo.archived:
                console.print(f"[yellow]Warning: Repository {repo_name} is archived[/yellow]")
            
            console.print(f"[green]Found repository: {repo_name}[/green]")
            
            if self.verbose:
                logger = logging.getLogger(__name__)
                logger.info(f"Retrieved repository {repo_name} from {self.org_name}")
            
            return repo
            
        except GithubException as e:
            if e.status == 404:
                console.print(f"[red]Repository {repo_name} not found in organization {self.org_name}[/red]")
            else:
                console.print(f"[red]Error accessing repository {repo_name}: {str(e)}[/red]")
            if self.verbose:
                logger = logging.getLogger(__name__)
                logger.error(f"GithubException when accessing repository {repo_name}: {str(e)}")
            return None
        except Exception as e:
            console.print(f"[red]Unexpected error getting repository {repo_name}: {str(e)}[/red]")
            if self.verbose:
                logger = logging.getLogger(__name__)
                logger.error(f"Unexpected error getting repository {repo_name}: {str(e)}")
            return None

    def analyze_repository(self, repo: Repository) -> Tuple[List[BuildTool], List[JavaVersion], List[PluginVersion]]:
        """
        Analyze a single repository for build tool versions, Java versions, and plugin versions
        
        This method examines a repository to find build tool versions, Java versions,
        and plugin versions. It checks files in order of reliability, stopping when
        it finds a version for each type to avoid duplicate entries.
        
        Args:
            repo: GitHub Repository object to analyze
            
        Returns:
            Tuple of (build_tools, java_versions, plugin_versions) found in the repository
        """
        build_tools = []
        java_versions = []
        plugin_versions = []
        
        if self.verbose:
            logging.info(f"Starting analysis of repository: {repo.name}")
        
        try:
            # Get repository contents from the default branch
            # Most build configurations are in the default branch
            self._make_api_call(f"Get contents for {repo.name}")
            contents = repo.get_contents("", ref=repo.default_branch)
            
            if self.verbose:
                logging.debug(f"Retrieved repository contents for {repo.name}")
            
            # Check each build tool type
            for tool_name, tool_config in self.build_tools.items():
                if self.verbose:
                    logging.debug(f"Checking for {tool_name} in {repo.name}")
                
                # Check files in order of reliability
                for file_name in tool_config['files']:
                    try:
                        # Try to get the file content
                        file_content = self._get_file_content(repo, file_name)
                        if file_content:
                            # Extract version using the defined patterns
                            version = self._extract_version(file_content, tool_config['version_patterns'])
                            if version:
                                if self.verbose:
                                    logging.info(f"Found {tool_name} version {version} in {repo.name} ({file_name})")
                                
                                # Found a version - create BuildTool object
                                build_tools.append(BuildTool(
                                    name=tool_name,
                                    version=version,
                                    file_path=file_name,
                                    repository=repo.name,
                                    branch=repo.default_branch,
                                    detection_method=f"Found in {file_name}"
                                ))
                                # Stop checking other files for this tool - we found the version
                                break
                            else:
                                if self.verbose:
                                    logging.debug(f"No {tool_name} version found in {file_name} for {repo.name}")
                    except Exception as e:
                        # File doesn't exist or can't be read - continue to next file
                        if self.verbose:
                            logging.debug(f"Error checking {file_name} in {repo.name}: {str(e)}")
                        continue
            
            # Check for Java versions
            for build_tool, java_config in self.java_version_patterns.items():
                if self.verbose:
                    logging.debug(f"Checking for Java version in {build_tool} config for {repo.name}")
                
                for file_name in java_config['files']:
                    try:
                        file_content = self._get_file_content(repo, file_name)
                        if file_content:
                            java_version = self._extract_java_version(file_content, java_config['patterns'], build_tool, file_name, repo.name, repo.default_branch)
                            if java_version:
                                if self.verbose:
                                    logging.info(f"Found Java version {java_version.version} in {repo.name} ({file_name})")
                                java_versions.append(java_version)
                                break  # Found Java version for this build tool
                    except Exception as e:
                        if self.verbose:
                            logging.debug(f"Error checking Java version in {file_name} for {repo.name}: {str(e)}")
                        continue
            
            # Check for plugin versions
            for build_tool, plugin_config in self.plugin_version_patterns.items():
                if self.verbose:
                    logging.debug(f"Checking for plugin version in {build_tool} config for {repo.name}")
                
                for file_name in plugin_config['files']:
                    try:
                        file_content = self._get_file_content(repo, file_name)
                        if file_content:
                            plugin_version = self._extract_plugin_version(file_content, plugin_config['patterns'], build_tool, file_name, repo.name, repo.default_branch)
                            if plugin_version:
                                if self.verbose:
                                    logging.info(f"Found plugin version {plugin_version.version} in {repo.name} ({file_name})")
                                plugin_versions.append(plugin_version)
                                break  # Found plugin version for this build tool
                    except Exception as e:
                        if self.verbose:
                            logging.debug(f"Error checking plugin version in {file_name} for {repo.name}: {str(e)}")
                        continue
            
            if self.verbose:
                logging.info(f"Completed analysis of {repo.name}: {len(build_tools)} build tools, {len(java_versions)} Java versions, {len(plugin_versions)} plugin versions")
                        
        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze {repo.name}: {str(e)}[/yellow]")
            if self.verbose:
                logging.error(f"Error analyzing {repo.name}: {str(e)}")
        
        return build_tools, java_versions, plugin_versions

    def analyze_repository_parallel(self, repo: Repository, progress_task=None) -> Tuple[List[BuildTool], List[JavaVersion], List[PluginVersion]]:
        """
        Analyze a single repository with progress tracking for parallel execution
        
        This method is a wrapper around analyze_repository that handles progress tracking
        for parallel execution. It's designed to work with ThreadPoolExecutor.
        
        Args:
            repo: GitHub Repository object to analyze
            progress_task: Rich progress task for updating progress bar
            
        Returns:
            Tuple of (build_tools, java_versions, plugin_versions) found in the repository
        """
        try:
            result = self.analyze_repository(repo)
            if progress_task:
                progress_task.advance(1)
            return result
        except Exception as e:
            if progress_task:
                progress_task.advance(1)
            console.print(f"[red]Error analyzing {repo.name}: {str(e)}[/red]")
            return [], [], []

    def _get_file_content(self, repo: Repository, file_path: str) -> Optional[str]:
        """
        Get file content from repository
        
        This method fetches the content of a specific file from a repository.
        It handles the GitHub API call and decodes the content properly.
        
        Args:
            repo: GitHub Repository object
            file_path: Path to the file within the repository
            
        Returns:
            File content as string, or None if file doesn't exist or can't be read
        """
        try:
            self._make_api_call(f"Get file {file_path} from {repo.name}")
            content = repo.get_contents(file_path, ref=repo.default_branch)
            if hasattr(content, 'decoded_content'):
                decoded_content = content.decoded_content.decode('utf-8', errors='ignore')
                if self.verbose:
                    logging.debug(f"Successfully retrieved {file_path} from {repo.name} ({len(decoded_content)} characters)")
                return decoded_content
        except Exception as e:
            # File doesn't exist or can't be read - this is expected for many files
            if self.verbose:
                logging.debug(f"Could not retrieve {file_path} from {repo.name}: {str(e)}")
        return None

    def _get_cache_path(self, cache_type: str) -> str:
        """
        Get the cache file path for a specific cache type
        
        Args:
            cache_type: Type of cache (e.g., 'all_repos', 'jenkins_repos')
            
        Returns:
            Full path to the cache file
        """
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        safe_org_name = self.org_name.replace('/', '_').replace('\\', '_')
        return os.path.join(self.cache_dir, f"{safe_org_name}_{cache_type}.pkl")
    
    def _load_from_cache(self, cache_type: str) -> Optional[List[Repository]]:
        """
        Load repository list from cache if available and fresh
        
        Args:
            cache_type: Type of cache to load
            
        Returns:
            List of repositories if cache is valid, None otherwise
        """
        if not self.use_cache:
            return None
        
        cache_path = self._get_cache_path(cache_type)
        
        if not os.path.exists(cache_path):
            if self.verbose:
                logging.debug(f"Cache file not found: {cache_path}")
            return None
        
        try:
            # Check if cache is still fresh
            cache_age = time.time() - os.path.getmtime(cache_path)
            if cache_age > self.cache_duration:
                if self.verbose:
                    logging.debug(f"Cache expired (age: {cache_age:.0f}s > {self.cache_duration}s): {cache_path}")
                return None
            
            # Load cached repositories
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
            
            if self.verbose:
                logging.info(f"Loaded {len(cached_data)} repositories from cache: {cache_path}")
                logging.debug(f"Cache age: {cache_age:.0f} seconds")
            
            console.print(f"[green]Loaded {len(cached_data)} repositories from cache[/green]")
            return cached_data
            
        except Exception as e:
            if self.verbose:
                logging.warning(f"Failed to load cache from {cache_path}: {str(e)}")
            return None
    
    def _save_to_cache(self, repositories: List[Repository], cache_type: str):
        """
        Save repository list to cache
        
        Args:
            repositories: List of repositories to cache
            cache_type: Type of cache to save
        """
        if not self.use_cache:
            return
        
        try:
            cache_path = self._get_cache_path(cache_type)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(repositories, f)
            
            if self.verbose:
                logging.info(f"Saved {len(repositories)} repositories to cache: {cache_path}")
            
            console.print(f"[green]Saved {len(repositories)} repositories to cache[/green]")
            
        except Exception as e:
            if self.verbose:
                logging.warning(f"Failed to save cache to {cache_path}: {str(e)}")
            console.print(f"[yellow]Warning: Failed to save cache: {str(e)}[/yellow]")

    def _extract_version(self, content: str, patterns: List[str]) -> Optional[str]:
        """
        Extract version from content using regex patterns
        
        This method applies regex patterns to extract version information from file content.
        It handles patterns with multiple capture groups (like Jenkins tool configurations)
        and returns the most relevant version found.
        
        Args:
            content: File content to search
            patterns: List of regex patterns to try
            
        Returns:
            Extracted version string, or None if no version found
        """
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                # Handle patterns with multiple groups (like Jenkins tool config)
                if len(match.groups()) > 1:
                    # Return the last non-None group (usually the version)
                    for group in reversed(match.groups()):
                        if group:
                            return group.strip()
                else:
                    return match.group(1).strip()
        return None

    def _extract_java_version(self, content: str, patterns: List[str], build_tool: str, file_path: str, repo_name: str, branch: str) -> Optional[JavaVersion]:
        """
        Extract Java version information from content using patterns
        
        Args:
            content: File content to search
            patterns: List of regex patterns to try
            build_tool: Which build tool this is for (maven/gradle)
            file_path: Path to the file being analyzed
            repo_name: Name of the repository
            branch: Branch being analyzed
            
        Returns:
            JavaVersion object with extracted information, or None if not found
        """
        source_compat = None
        target_compat = None
        version = None
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                
                # Determine what type of version this is
                if 'source' in pattern.lower():
                    source_compat = extracted
                elif 'target' in pattern.lower():
                    target_compat = extracted
                elif 'java.version' in pattern.lower():
                    version = extracted
                else:
                    # Default to version if we can't determine type
                    version = extracted
        
        # If we found any Java version information, create the object
        if version or source_compat or target_compat:
            # Determine the primary version to display
            primary_version = version or source_compat or target_compat
            
            # Clean up version strings (remove 'VERSION_' prefix, etc.)
            if primary_version and primary_version.startswith('VERSION_'):
                primary_version = primary_version.replace('VERSION_', '')
            
            return JavaVersion(
                version=primary_version,
                source_compatibility=source_compat,
                target_compatibility=target_compat,
                file_path=file_path,
                repository=repo_name,
                branch=branch,
                detection_method=f"Found in {build_tool} configuration"
            )
        
        return None

    def _extract_plugin_version(self, content: str, patterns: List[str], build_tool: str, file_path: str, repo_name: str, branch: str) -> Optional[PluginVersion]:
        """
        Extract plugin version information from file content
        
        This method searches for plugin version patterns in the given content
        and returns a PluginVersion object if found.
        
        Args:
            content: File content to search in
            patterns: List of regex patterns to search for
            build_tool: The build tool being analyzed (e.g., 'gradle')
            file_path: Path to the file being analyzed
            repo_name: Name of the repository
            branch: Branch being analyzed
            
        Returns:
            PluginVersion object if found, None otherwise
        """
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return PluginVersion(
                        plugin_name="publishPluginVersion",
                        version=extracted,
                        file_path=file_path,
                        repository=repo_name,
                        branch=branch,
                        detection_method=f"Found in {build_tool} configuration"
                    )
        
        return None

    def generate_report(self, all_build_tools: List[BuildTool], all_java_versions: List[JavaVersion], all_plugin_versions: List[PluginVersion] = None, jenkins_only: bool = False):
        """
        Generate a comprehensive report of build tool versions, Java versions, and plugin versions found
        
        This method creates both a summary view (grouped by tool and version)
        and a detailed table showing all findings. The summary helps identify
        version distribution across the organization.
        
        Args:
            all_build_tools: List of all BuildTool objects found across all repositories
            all_java_versions: List of all JavaVersion objects found across all repositories
            all_plugin_versions: List of all PluginVersion objects found across all repositories
            jenkins_only: Whether this was a Jenkins-only analysis
        """
        console.print("\n" + "="*80)
        console.print("[bold blue]BUILD TOOL, JAVA VERSION, AND PLUGIN VERSION ANALYSIS REPORT[/bold blue]")
        console.print("="*80)
        
        # Show analysis mode
        if jenkins_only:
            console.print("\n[bold green]ANALYSIS MODE: Jenkins-only[/bold green]")
            console.print("-" * 30)
            console.print("[green]Only repositories with Jenkinsfiles were analyzed[/green]")
            console.print()
        else:
            console.print("\n[bold blue]ANALYSIS MODE: Full analysis[/bold blue]")
            console.print("-" * 30)
            console.print("[blue]All repositories were analyzed[/blue]")
            console.print()
        
        # Important clarification
        console.print("[bold yellow]IMPORTANT:[/bold yellow]")
        console.print("[yellow]This report shows:[/yellow]")
        console.print("[yellow]  • Build tool versions (Maven, Gradle) - the tools used to compile code[/yellow]")
        console.print("[yellow]  • Java versions - the Java version the application is built with[/yellow]")
        console.print("[yellow]  • Plugin versions - plugin versions found in gradle.properties files[/yellow]")
        console.print()
        
        # Build Tools Summary
        if all_build_tools:
            console.print("[bold green]BUILD TOOL VERSIONS FOUND:[/bold green]")
            console.print("-" * 40)
            
            tool_summary = {}
            for tool in all_build_tools:
                if tool.name not in tool_summary:
                    tool_summary[tool.name] = {'versions': set(), 'repos': set()}
                tool_summary[tool.name]['versions'].add(tool.version)
                tool_summary[tool.name]['repos'].add(tool.repository)
            
            for tool_name, data in tool_summary.items():
                console.print(f"\n[bold]{tool_name.upper()} BUILD TOOL VERSIONS:[/bold]")
                for version in sorted(data['versions']):
                    repos_with_version = [repo for repo in data['repos'] 
                                        if any(t.version == version and t.repository == repo 
                                              for t in all_build_tools if t.name == tool_name)]
                    console.print(f"  [bold]Version: {version}[/bold] - Used in {len(repos_with_version)} repositories")
                    for repo in sorted(repos_with_version):
                        console.print(f"    • {repo}")
        
        # Java Versions Summary
        if all_java_versions:
            console.print(f"\n[bold green]JAVA VERSIONS FOUND:[/bold green]")
            console.print("-" * 40)
            console.print("[dim]These are the Java versions the applications are built with[/dim]")
            console.print()
            
            java_summary = {}
            for java in all_java_versions:
                if java.version not in java_summary:
                    java_summary[java.version] = {'repos': set()}
                java_summary[java.version]['repos'].add(java.repository)
            
            for version in sorted(java_summary.keys()):
                repos_with_version = list(java_summary[version]['repos'])
                console.print(f"  [bold]Java Version: {version}[/bold] - Used in {len(repos_with_version)} repositories")
                for repo in sorted(repos_with_version):
                    console.print(f"    • {repo}")
        
        # Plugin Versions Summary
        if all_plugin_versions:
            console.print(f"\n[bold green]PLUGIN VERSIONS FOUND:[/bold green]")
            console.print("-" * 40)
            console.print("[dim]These are plugin versions found in gradle.properties files[/dim]")
            console.print()
            
            plugin_summary = {}
            for plugin in all_plugin_versions:
                if plugin.plugin_name not in plugin_summary:
                    plugin_summary[plugin.plugin_name] = {'versions': set(), 'repos': set()}
                plugin_summary[plugin.plugin_name]['versions'].add(plugin.version)
                plugin_summary[plugin.plugin_name]['repos'].add(plugin.repository)
            
            for plugin_name, data in plugin_summary.items():
                console.print(f"\n[bold]{plugin_name.upper()} PLUGIN VERSIONS:[/bold]")
                for version in sorted(data['versions']):
                    repos_with_version = [repo for repo in data['repos'] 
                                        if any(p.version == version and p.repository == repo 
                                              for p in all_plugin_versions if p.plugin_name == plugin_name)]
                    console.print(f"  [bold]Version: {version}[/bold] - Used in {len(repos_with_version)} repositories")
                    for repo in sorted(repos_with_version):
                        console.print(f"    • {repo}")
        
        # Detailed table
        if all_build_tools or all_java_versions or all_plugin_versions:
            table = Table(title="Detailed Analysis")
            table.add_column("Repository", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Name", style="green")
            table.add_column("Version", style="yellow")
            table.add_column("Config File", style="blue")
            table.add_column("Detection Method", style="red")
            
            # Add build tools
            for tool in all_build_tools:
                table.add_row(
                    tool.repository,
                    "Build Tool",
                    tool.name,
                    tool.version,
                    tool.file_path,
                    tool.detection_method
                )
            
            # Add Java versions
            for java in all_java_versions:
                table.add_row(
                    java.repository,
                    "Java Version",
                    "Java",
                    java.version,
                    java.file_path,
                    java.detection_method
                )
            
            # Add plugin versions
            for plugin in all_plugin_versions:
                table.add_row(
                    plugin.repository,
                    "Plugin Version",
                    plugin.plugin_name,
                    plugin.version,
                    plugin.file_path,
                    plugin.detection_method
                )
            
            console.print(table)

@click.command()
@click.option('--org', required=True, help='GitHub organization name')
@click.option('--repo', help='Specific repository name to analyze (e.g., "my-repo"). If not specified, analyzes all repositories in the organization.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub personal access token')
@click.option('--output', '-o', help='Output file for JSON report')
@click.option('--jenkins-only', is_flag=True, help='Only analyze repositories with Jenkinsfiles (much faster)')
@click.option('--rate-limit-delay', default=0.05, help='Delay between API calls in seconds (default: 0.05)')
@click.option('--max-workers', default=8, help='Maximum number of parallel workers (default: 8)')
@click.option('--verbose', is_flag=True, help='Enable verbose logging for detailed API request information')
@click.option('--use-cache', is_flag=True, help='Enable caching of repository lists to reduce API calls during development')
@click.option('--cache-dir', default='.cache', help='Directory to store cache files (default: .cache)')
@click.option('--clear-cache', is_flag=True, help='Clear all cache files before running analysis')
def main(org: str, repo: str, token: str, output: str, jenkins_only: bool, rate_limit_delay: float, max_workers: int, verbose: bool, use_cache: bool, cache_dir: str, clear_cache: bool):
    """
    Analyze GitHub organization or specific repository for build tool versions, Java versions, and plugin versions
    
    This script scans repositories in a GitHub organization (or a specific repository) to find
    the versions of build tools (Maven, Gradle), Java versions, and plugin versions
    being used. It focuses on the most reliable sources of version information
    and provides both console output and optional JSON export.
    
    Key Features:
    - Rate limiting to respect GitHub API limits
    - Parallel processing for efficient analysis of large organizations
    - Single repository analysis mode for targeted analysis
    - Focus on wrapper files and Jenkins configurations for accuracy
    - Clear reporting of how each version was detected
    - Jenkins-only mode for faster analysis of CI/CD repositories
    - Plugin version detection from gradle.properties files
    """
    
    if not token:
        console.print("[red]Error: GitHub token is required. Set GITHUB_TOKEN environment variable or use --token option.[/red]")
        return
    
    try:
        # Setup logging
        logger = setup_logging(verbose)
        
        if verbose:
            logger.info("Verbose logging enabled - detailed API request information will be shown")
            console.print("[bold green]Verbose logging enabled[/bold green]")

        # Initialize analyzer with configuration
        analyzer = SimpleBuildAnalyzer(token, org, rate_limit_delay, max_workers, verbose, use_cache, cache_dir)
        
        # Show cache status
        if use_cache:
            console.print(f"[bold green]Caching enabled[/bold green] - Cache directory: {cache_dir}")
            console.print("[green]Repository lists will be cached for 1 hour to reduce API calls[/green]")
        else:
            console.print("[dim]Caching disabled - use --use-cache to enable[/dim]")
        
        # Clear cache if requested
        if clear_cache:
            console.print(f"[bold red]Clearing cache in {cache_dir}...[/bold red]")
            if os.path.exists(cache_dir):
                for cache_file in os.listdir(cache_dir):
                    if cache_file.endswith('.pkl'):
                        try:
                            os.remove(os.path.join(cache_dir, cache_file))
                            console.print(f"[green]Cleared {cache_file}[/green]")
                        except Exception as e:
                            console.print(f"[red]Error clearing {cache_file}: {str(e)}[/red]")
                console.print("[green]Cache cleared.[/green]")
            else:
                console.print("[yellow]Cache directory does not exist.[/yellow]")
            return # Exit after clearing cache

        # Display initial rate limit status for monitoring
        try:
            rate_limit = analyzer.github.get_rate_limit()
            console.print(f"[blue]GitHub API Rate Limit: {rate_limit.core.remaining}/{rate_limit.core.limit} requests remaining[/blue]")
            reset_timestamp = rate_limit.core.reset.timestamp()
            console.print(f"[blue]Rate limit resets at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reset_timestamp))}[/blue]")
            
            if verbose:
                logger.info(f"Initial rate limit status:")
                logger.info(f"  - Remaining requests: {rate_limit.core.remaining}/{rate_limit.core.limit}")
                logger.info(f"  - Reset time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reset_timestamp))}")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not check rate limit: {str(e)}[/yellow]")
            if verbose:
                logger.warning(f"Could not check initial rate limit: {str(e)}")
        
        # Get repositories based on analysis mode
        if repo:
            # Single repository mode
            console.print(f"[bold blue]Single repository mode - analyzing repository: {repo}[/bold blue]")
            single_repo = analyzer.get_specific_repository(repo)
            if not single_repo:
                console.print(f"[red]Repository {repo} not found or not accessible[/red]")
                return
            repos = [single_repo]
        elif jenkins_only:
            console.print("[bold green]Using Jenkins-only mode - analyzing only repositories with Jenkinsfiles[/bold green]")
            repos = analyzer.search_repos_with_jenkinsfiles()
        else:
            console.print("[bold blue]Using full analysis mode - analyzing all repositories[/bold blue]")
            repos = analyzer.get_repositories()
        
        if not repos:
            console.print("[yellow]No repositories found to analyze[/yellow]")
            return
        
        # Analyze repositories in parallel for efficiency
        all_build_tools = []
        all_java_versions = []
        all_plugin_versions = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Analyzing {len(repos)} repositories with {max_workers} workers...", 
                total=len(repos)
            )
            
            # Use ThreadPoolExecutor for parallel processing
            # This dramatically speeds up analysis of large organizations
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all repository analysis tasks
                future_to_repo = {}
                for repo in repos:
                    future = executor.submit(analyzer.analyze_repository_parallel, repo, task)
                    future_to_repo[future] = repo.name
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_repo):
                    repo_name = future_to_repo[future]
                    try:
                        build_tools, java_versions, plugin_versions = future.result()
                        all_build_tools.extend(build_tools)
                        all_java_versions.extend(java_versions)
                        all_plugin_versions.extend(plugin_versions)
                    except Exception as e:
                        console.print(f"[red]Error analyzing {repo_name}: {str(e)}[/red]")
        
        # Generate and display the analysis report
        analyzer.generate_report(all_build_tools, all_java_versions, all_plugin_versions, jenkins_only)
        
        # Display final statistics for monitoring and verification
        console.print(f"\n[bold green]Analysis Complete![/bold green]")
        console.print(f"[blue]Total repositories analyzed: {len(repos)}[/blue]")
        console.print(f"[blue]Total build tools found: {len(all_build_tools)}[/blue]")
        console.print(f"[blue]Total Java versions found: {len(all_java_versions)}[/blue]")
        console.print(f"[blue]Total plugin versions found: {len(all_plugin_versions)}[/blue]")
        console.print(f"[blue]Total API calls made: {analyzer.api_calls_made}[/blue]")
        console.print(f"[blue]Parallel workers used: {max_workers}[/blue]")
        
        if verbose:
            logger.info(f"Analysis completed successfully:")
            logger.info(f"  - Total repositories analyzed: {len(repos)}")
            logger.info(f"  - Total build tools found: {len(all_build_tools)}")
            logger.info(f"  - Total Java versions found: {len(all_java_versions)}")
            logger.info(f"  - Total plugin versions found: {len(all_plugin_versions)}")
            logger.info(f"  - Total API calls made: {analyzer.api_calls_made}")
            logger.info(f"  - Parallel workers used: {max_workers}")
        
        # Show remaining API calls for monitoring
        try:
            final_rate_limit = analyzer.github.get_rate_limit()
            console.print(f"[blue]Remaining API calls: {final_rate_limit.core.remaining}/{final_rate_limit.core.limit}[/blue]")
            
            if verbose:
                logger.info(f"Final rate limit status:")
                logger.info(f"  - Remaining requests: {final_rate_limit.core.remaining}/{final_rate_limit.core.limit}")
                logger.info(f"  - Requests used: {final_rate_limit.core.limit - final_rate_limit.core.remaining}")
        except Exception as e:
            if verbose:
                logger.warning(f"Could not check final rate limit: {str(e)}")
        
        # Save JSON report if requested
        # This provides structured data for further analysis or integration
        if output:
            # Determine analysis mode for report
            if repo:
                analysis_mode = 'single_repository'
            elif jenkins_only:
                analysis_mode = 'jenkins_only'
            else:
                analysis_mode = 'full_analysis'
            
            report_data = {
                'organization': org,
                'target_repository': repo if repo else None,
                'analysis_mode': analysis_mode,
                'build_tools': [
                    {
                        'repository': tool.repository,
                        'build_tool': tool.name,
                        'build_tool_version': tool.version,
                        'file_path': tool.file_path,
                        'detection_method': tool.detection_method
                    }
                    for tool in all_build_tools
                ],
                'java_versions': [
                    {
                        'repository': java.repository,
                        'java_version': java.version,
                        'source_compatibility': java.source_compatibility,
                        'target_compatibility': java.target_compatibility,
                        'file_path': java.file_path,
                        'detection_method': java.detection_method
                    }
                    for java in all_java_versions
                ],
                'plugin_versions': [
                    {
                        'repository': plugin.repository,
                        'plugin_name': plugin.plugin_name,
                        'plugin_version': plugin.version,
                        'file_path': plugin.file_path,
                        'detection_method': plugin.detection_method
                    }
                    for plugin in all_plugin_versions
                ],
                'summary': {
                    'total_repositories_analyzed': len(repos),
                    'total_build_tools_found': len(all_build_tools),
                    'total_java_versions_found': len(all_java_versions),
                    'total_plugin_versions_found': len(all_plugin_versions),
                    'api_calls_made': analyzer.api_calls_made,
                    'parallel_workers_used': max_workers
                }
            }
            
            with open(output, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            console.print(f"\n[green]JSON report saved to: {output}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

# Alias for compatibility with tests and legacy code
BuildAnalyzer = SimpleBuildAnalyzer

if __name__ == '__main__':
    main() 