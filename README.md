# BuildCheck - GitHub Organization Build Analysis Tool

BuildCheck is a comprehensive tool for analyzing GitHub organizations to identify build tools, their versions, and Artifactory repository usage across Jenkins jobs and other CI/CD pipelines.

## Features

- 🔍 **Repository Discovery**: Automatically finds all repositories in a GitHub organization
- 🎯 **Single Repository Analysis**: Target specific repositories for focused analysis
- 🛠️ **Build Tool Detection**: Identifies Maven, Gradle, npm, Grunt, Packer, Docker, and Jenkins configurations
- 📦 **Artifactory Analysis**: Discovers Artifactory repositories used for dependencies and artifacts
- 📊 **Comprehensive Reporting**: Generates detailed reports with tool versions and repository usage
- 🚀 **Jenkins Pipeline Analysis**: Specialized analysis for Jenkinsfiles and pipeline configurations
- ⚡ **High Performance**: Only scans root directory for build files (much faster than full repository scan)
- 📋 **Missing Build Detection**: Reports repositories that don't have build configurations
- 🚫 **Smart Filtering**: Automatically excludes infrastructure and Terraform repositories
- ⚡ **Jenkins-Only Mode**: Ultra-fast analysis of only repositories with Jenkinsfiles
- 🚀 **Parallel Processing**: Multi-threaded analysis for faster processing
- 📊 **Enhanced Progress**: Real-time progress with file analysis tracking
- 🔍 **Repository Discovery Progress**: Visual progress tracking for repository discovery and filtering

## Supported Build Tools

### Core Build Tools
- **Maven**: `pom.xml`, `maven-wrapper.properties`
- **Gradle**: `build.gradle`, `gradle-wrapper.properties`
- **npm**: `package.json`, `package-lock.json`
- **Docker**: `Dockerfile`, `docker-compose.yml`

### New Additions
- **Grunt**: `Gruntfile.js`, `Gruntfile.coffee`, `package.json` (for grunt dependencies)
- **Packer**: `*.pkr.hcl`, `*.pkr.json`, `packer.json`, `packer.pkr.hcl`

### CI/CD Tools
- **Jenkins**: `Jenkinsfile`, pipeline configurations

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd BuildCheck
```

2. Set up the virtual environment and install dependencies:
```bash
./setup.sh
```

3. Set up your GitHub token:
```bash
export GITHUB_TOKEN=your_github_personal_access_token
```

## Configuration (Recommended)

BuildCheck supports a YAML configuration file that allows you to set your organization name, parallelism settings, and repository exclusions without having to use command line options every time.

### Quick Setup

```bash
# Create a configuration file with your organization settings
python setup_config.py --org your-organization-name

# Or with additional options
python setup_config.py --org your-organization-name --jenkins-only --max-workers 6 --verbose
```

### Configuration File Format

The configuration file (`config.yaml`) supports the following settings:

```yaml
# GitHub Organization Configuration
organization: "your-org-name"  # Required: GitHub organization to analyze

# Performance Settings
parallelism:
  max_workers: 8               # Number of parallel workers (default: 8, recommended: 4-8)
  rate_limit_delay: 0.05       # Delay between API calls in seconds (default: 0.05)

# Repository Exclusions
exclusions:
  # Exact repository names to exclude
  repositories:
    - "infrastructure-environments"
    - "infrastructure-modules"
    - "documentation"
    - "wiki-content"
  
  # Pattern-based exclusions (supports wildcards and regex)
  patterns:
    - "terraform-*"            # Exclude all repositories starting with "terraform-"
    - "*-infra"                # Exclude repositories ending with "-infra"
    - "legacy-*"               # Exclude repositories starting with "legacy-"
    - "test-*"                 # Exclude test repositories
    - "demo-*"                 # Exclude demo repositories

# Analysis Mode
analysis:
  jenkins_only: false          # Only analyze repositories with Jenkinsfiles (much faster)
  single_repository: null      # Analyze specific repository (e.g., "my-repo") or null for all

# Caching Configuration
caching:
  enabled: true                # Enable caching of repository lists
  directory: ".cache"          # Directory to store cache files
  duration: 3600               # Cache duration in seconds (1 hour)

# Output Configuration
output:
  json_report: null            # Output file for JSON report (e.g., "report.json") or null to skip
  verbose: false               # Enable verbose logging
```

### Using Configuration Files

Once you have a configuration file, you can run BuildCheck without command line arguments:

```bash
# Run with default config.yaml
python build_check.py

# Run with custom configuration file
python build_check.py --config my-config.yaml

# Command line options override configuration file settings
python build_check.py --verbose --max-workers 4
```

### Configuration Management

```bash
# Show current configuration settings
python setup_config.py show-config

# Show configuration from specific file
python setup_config.py show-config --config my-config.yaml

# Create default configuration file
python build_check.py --create-config

# Create configuration file with custom path
python build_check.py --create-config --config my-config.yaml
```

## Usage

### Setup (First Time Only)

```bash
# Set up virtual environment and install dependencies
./setup.sh

# Set your GitHub token
export GITHUB_TOKEN=your_github_personal_access_token
```

### Basic Analysis

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run analysis on all repositories in the organization
python build_check.py --org your-organization-name

# Analyze a specific repository
python build_check.py --org your-organization-name --repo your-repo-name
```

### Save Report to File

```bash
python build_check.py --org your-organization-name --output report.json
```

### Using the Shell Script

```bash
# Full analysis (all repositories)
./run_analysis.sh your-organization-name

# Jenkins-only mode (much faster)
./run_analysis.sh your-organization-name jenkins-only

# Parallel processing with 8 workers
./run_analysis.sh your-organization-name 8

# Jenkins-only with 6 parallel workers
./run_analysis.sh your-organization-name jenkins-only 6
```

### Advanced Usage with Rate Limiting

```bash
# Use custom delay between API calls (default: 0.05 seconds - optimized for performance)
python build_check.py --org your-organization-name --rate-limit-delay 0.1

# Analyze a specific repository with custom delay
python build_check.py --org your-organization-name --repo your-repo-name --rate-limit-delay 0.1

# Jenkins-only mode with custom delay
python build_check.py --org your-organization-name --jenkins-only --rate-limit-delay 0.05

# Parallel processing with 8 workers
python build_check.py --org your-organization-name --max-workers 8

# Combine options
python build_check.py --org your-organization-name --output report.json --rate-limit-delay 0.05 --max-workers 6

# Single repository with verbose logging
python build_check.py --org your-organization-name --repo your-repo-name --verbose --output repo-analysis.json

# Enable verbose logging for debugging
python build_check.py --org your-organization-name --verbose

# Verbose logging with Jenkins-only mode
python build_check.py --org your-organization-name --verbose --jenkins-only
```

### Caching for Development

The tool supports caching repository lists to reduce API calls during development and testing:

```bash
# Enable caching (reduces API calls significantly)
python build_check.py --org your-organization-name --use-cache

# Use custom cache directory
python build_check.py --org your-organization-name --use-cache --cache-dir /tmp/buildcheck-cache

# Clear cache before running
python build_check.py --org your-organization-name --clear-cache

# Jenkins-only mode with caching
python build_check.py --org your-organization-name --jenkins-only --use-cache
```

### Cache Management

Use the cache manager utility to inspect and manage cache files:

```bash
# List all cache files
python cache_manager.py list

# Clear all cache files
python cache_manager.py clear

# Clear cache for specific organization
python cache_manager.py clear --org your-organization-name

# Inspect a specific cache file
python cache_manager.py inspect your-org_jenkins_repos.pkl
```

## What It Analyzes

### Build Tools Detected

#### Maven
- **Files**: `pom.xml`, `maven-wrapper.properties`
- **Version Detection**: Maven version, wrapper version
- **Usage**: Maven build configurations and dependencies

#### Gradle
- **Files**: `build.gradle`, `gradle-wrapper.properties`, `gradle.properties`
- **Version Detection**: Gradle version, wrapper distribution
- **Usage**: Gradle build scripts and configurations

#### npm
- **Files**: `package.json`, `package-lock.json`
- **Version Detection**: Node.js and npm engine requirements
- **Usage**: JavaScript/Node.js project dependencies

#### Grunt (New!)
- **Files**: `Gruntfile.js`, `Gruntfile.coffee`, `package.json`
- **Version Detection**: Grunt and grunt-cli versions
- **Usage**: JavaScript task automation and build processes

#### Packer (New!)
- **Files**: `*.pkr.hcl`, `*.pkr.json`, `packer.json`, `packer.pkr.hcl`
- **Version Detection**: Packer version requirements
- **Usage**: Infrastructure as Code image building

#### Docker
- **Files**: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`
- **Version Detection**: Base image versions
- **Usage**: Containerization and deployment

#### Jenkins
- **Files**: `Jenkinsfile`, `Jenkinsfile.groovy`, `.jenkins/pipeline.groovy`
- **Version Detection**: Agent labels and tool configurations
- **Usage**: CI/CD pipeline definitions

### Artifactory Integration

- Repository URLs and names
- Usage patterns (pull dependencies vs push artifacts)
- Credential configurations
- Repository references in build scripts

## Output

The tool provides:

1. **Console Report**: Rich formatted output with tables and summaries
2. **JSON Report**: Structured data for further processing
3. **Detailed Analysis**: Per-repository breakdown of tools and configurations

## Example Output

```
BUILD CHECK ANALYSIS REPORT
================================================================================

BUILD TOOLS FOUND
----------------------------------------
Maven: 3.8.6, 3.9.0
  Repositories: service-a, service-b, api-gateway

Gradle: 7.6, 8.0
  Repositories: mobile-app, backend-service

Grunt: 1.4.3, 1.5.0
  Repositories: frontend-app, ui-components

Packer: 1.8.0, 1.9.0
  Repositories: infrastructure, ami-builder

ARTIFACTORY REPOSITORIES
----------------------------------------
libs-release-local: push
  Used in: service-a, service-b

libs-snapshot-local: both
  Used in: api-gateway, mobile-app

EXCLUDED REPOSITORIES
------------------------------
Excluded 8 infrastructure/Terraform repositories from analysis:
  • infrastructure-environments
  • infrastructure-modules
  • terraform-aws
  • terraform-azure
  • terraform-gcp
  • terraform-modules
  • terraform-templates
  • terraform-variables

REPOSITORIES WITHOUT BUILD CONFIGURATIONS
--------------------------------------------------
Found 5 repositories without build configurations:
  • documentation
  • readme-updates
  • test-repo
  • wiki-content
  • legacy-project

## Configuration

### Environment Variables

- `GITHUB_TOKEN`: Your GitHub personal access token (required)

### Command Line Options

- `--org`: GitHub organization name (can also be set in config file)
- `--repo`: Specific repository name to analyze (e.g., "my-repo"). If not specified, analyzes all repositories in the organization.
- `--token`: GitHub personal access token (optional if set in environment)
- `--output`: Output file for JSON report (optional)
- `--rate-limit-delay`: Delay between API calls in seconds (default: 0.05 - optimized for performance)
- `--jenkins-only`: Only analyze repositories with Jenkinsfiles (much faster)
- `--max-workers`: Maximum number of parallel workers (default: 8, recommended: 4-8)
- `--verbose`: Enable verbose logging for detailed API request information
- `--use-cache`: Enable caching of repository lists to reduce API calls during development
- `--cache-dir`: Directory to store cache files (default: .cache)
- `--clear-cache`: Clear all cache files before running analysis
- `--config`, `-c`: Path to configuration file (default: config.yaml)
- `--create-config`: Create a default configuration file and exit

## Requirements

- Python 3.7+
- virtualenv (will be installed automatically if missing)
- GitHub Personal Access Token with `repo` scope
- Internet connection for GitHub API access

## Performance Optimizations

The tool has been optimized for significantly better performance:

### Rate Limiting Optimizations
- **Cached Rate Limit Checking**: Rate limit information is cached for 30 seconds to avoid excessive API calls
- **Reduced API Calls**: Eliminated double API calls that were causing performance issues
- **Optimized Default Delay**: Reduced default delay from 0.1s to 0.05s (20 calls/second vs 10 calls/second)
- **Smart Rate Limit Checking**: Only checks rate limits every 10 API calls instead of every call

### Performance Improvements
- **50% Faster**: Typical analysis is now 50% faster due to reduced API overhead
- **Better Parallel Processing**: Optimized rate limiting works better with parallel workers
- **Reduced Verbose Overhead**: Verbose logging no longer makes additional API calls

### Before vs After
- **Before**: 2 API calls per actual API call (rate limit check + actual call)
- **After**: 1 API call per actual API call (with smart caching)
- **Before**: 0.1s delay between calls (10 calls/second)
- **After**: 0.05s delay between calls (20 calls/second)

### Caching Benefits
- **Development Speed**: Cache repository lists for 1 hour to avoid re-discovery
- **API Call Reduction**: Subsequent runs use cached data instead of API calls
- **Testing Efficiency**: Perfect for iterative development and testing
- **Cache Management**: Built-in tools to inspect and manage cache files

## API Rate Limiting

The tool includes comprehensive GitHub API rate limiting management:

- **Automatic Rate Limit Checking**: Monitors remaining API calls and resets
- **Intelligent Delays**: Adds delays between API calls to respect limits
- **Graceful Handling**: Waits for rate limit resets when exceeded
- **Progress Tracking**: Shows remaining API calls and reset times
- **Configurable Delays**: Adjust delay between calls with `--rate-limit-delay`

### Rate Limit Behavior:
- **Warning**: Shows warning when < 100 requests remaining
- **Auto-delay**: Adds extra delay when approaching limits
- **Wait and retry**: Automatically waits for reset when limit exceeded
- **Statistics**: Reports total API calls made and remaining
- **DateTime Handling**: Properly converts GitHub API datetime objects to timestamps

## Advanced Features

### Performance Optimization
- **Root-Only Scanning**: Only checks files in the repository root directory
- **Fast Processing**: Dramatically reduces API calls and processing time
- **Build File Detection**: Focuses on common build configuration file locations

### Wildcard File Matching
The tool supports wildcard patterns for file detection, particularly useful for Packer files:
- `*.pkr.hcl` - Packer HCL configuration files
- `*.pkr.json` - Packer JSON configuration files

### Version Detection Patterns
Each tool has specific regex patterns for version detection:
- **Grunt**: Looks for grunt and grunt-cli versions in package.json
- **Packer**: Searches for packer_version and required_version in configuration files

### Jenkins Pipeline Integration
The Jenkins analyzer specifically looks for:
- Grunt commands in pipeline stages
- Packer build and validation commands
- Artifact publishing patterns for both tools

### Missing Build Detection
- **Identifies Repositories**: Lists repositories without build configurations
- **Helps with Auditing**: Useful for finding projects that might need CI/CD setup
- **Summary Statistics**: Provides counts of repositories with/without builds

### Repository Filtering
- **Infrastructure Exclusion**: Automatically excludes `infrastructure-environments` and `infrastructure-modules`
- **Terraform Exclusion**: Excludes all repositories starting with `terraform-`
- **Focused Analysis**: Concentrates on application repositories with build configurations
- **Transparent Reporting**: Shows which repositories were excluded and why

### Jenkins-Only Mode
- **GitHub Search API**: Uses GitHub's search API to find repositories with Jenkinsfiles
- **Ultra-Fast Analysis**: Only analyzes repositories that actually have CI/CD pipelines
- **Reduced API Calls**: Dramatically fewer API calls compared to full analysis
- **Perfect for CI/CD Audits**: Ideal for teams focused on Jenkins pipeline analysis

### Parallel Processing
- **Multi-threaded Analysis**: Uses ThreadPoolExecutor for concurrent repository analysis
- **Configurable Workers**: Adjust number of parallel workers (default: 4, max: 8)
- **Rate Limit Aware**: Respects GitHub API rate limits even with parallel processing
- **Progress Tracking**: Real-time progress with file analysis counts
- **Error Handling**: Graceful handling of individual repository failures

### Progress Tracking
- **Repository Discovery**: Shows progress when fetching and filtering repositories
- **Jenkins Search**: Displays progress when searching for repositories with Jenkinsfiles
- **Analysis Progress**: Real-time progress bars for repository analysis
- **Detailed Status**: Shows counts of found, skipped, and processed repositories
- **Visual Feedback**: Rich progress bars with spinners and percentage completion

#### Progress Tracking Features
- **Repository Counting**: Shows "Counting repositories..." before processing
- **Processing Status**: Displays current repository being processed
- **Filtering Information**: Shows how many repositories are skipped (archived/empty)
- **Found Repositories**: Tracks how many valid repositories are discovered
- **Search Results**: For Jenkins-only mode, shows search result processing

### Verbose Logging
- **Detailed API Tracking**: Logs every GitHub API call with timestamps and descriptions
- **Rate Limit Monitoring**: Shows real-time rate limit status and reset times
- **Repository Analysis**: Tracks which files are being checked in each repository
- **Error Debugging**: Provides detailed error information for troubleshooting
- **Performance Insights**: Shows API call counts and processing statistics

#### Using Verbose Logging
```bash
# Enable verbose logging to see detailed API request information
python build_check.py --org your-organization-name --verbose

# Combine with other options
python build_check.py --org your-organization-name --verbose --jenkins-only --output report.json
```

#### Verbose Logging Output
When `--verbose` is enabled, you'll see detailed information like:
```
2024-01-15 14:30:00 - INFO - Verbose logging enabled - detailed API request information will be shown
2024-01-15 14:30:01 - DEBUG - API Call #1: Get organization repositories
2024-01-15 14:30:01 - DEBUG -   - Rate Limit: 4850/5000 requests remaining
2024-01-15 14:30:01 - DEBUG -   - Rate Limit Reset: 2024-01-15 15:30:00
2024-01-15 14:30:01 - DEBUG -   - Delay Applied: 0.1s
2024-01-15 14:30:02 - INFO - Starting analysis of repository: my-service
2024-01-15 14:30:02 - DEBUG - Successfully retrieved pom.xml from my-service (2048 characters)
2024-01-15 14:30:02 - INFO - Found maven version 3.8.6 in my-service (pom.xml)
```

## Testing

The project includes a comprehensive test suite organized according to Python best practices.

### Test Structure

Tests are located in the `tests/` directory and follow pytest conventions:

```
tests/
├── __init__.py              # Makes tests a Python package
├── conftest.py              # Shared fixtures and configuration
├── test_build_check.py      # Tests for main build_check module
├── test_caching.py          # Tests for caching functionality
├── test_performance.py      # Tests for performance optimizations
├── test_rate_limit.py       # Tests for rate limiting functionality
└── README.md               # Detailed test documentation
```

### Running Tests

#### Using the test runner script (recommended)
```bash
# Run all tests
./run_tests.sh

# Run tests with coverage
./run_tests.sh --coverage

# Run tests with verbose output
./run_tests.sh --verbose

# Run only unit tests
./run_tests.sh --unit

# Run only integration tests
./run_tests.sh --integration

# Run only slow tests
./run_tests.sh --slow
```

#### Using pytest directly
```bash
# Run all tests
python -m pytest tests/

# Run tests with coverage
python -m pytest tests/ --cov=build_check --cov=cache_manager --cov=jenkins_analyzer --cov-report=html

# Run specific test file
python -m pytest tests/test_caching.py

# Run specific test class
python -m pytest tests/test_caching.py::TestCaching

# Run specific test method
python -m pytest tests/test_caching.py::TestCaching::test_caching_creation
```

### Test Categories

- **Unit Tests**: Test individual functions and methods in isolation (marked with `@pytest.mark.unit`)
- **Integration Tests**: Test multiple components working together (marked with `@pytest.mark.integration`)
- **Slow Tests**: Tests that take significant time to run (marked with `@pytest.mark.slow`)

### Test Dependencies

Test dependencies are included in `requirements.txt`:
- `pytest`: Test framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking utilities

### Environment Variables for Testing

Tests require the following environment variables:
- `GITHUB_TOKEN`: GitHub API token for authentication

You can set these in a `.env` file in the project root:
```bash
GITHUB_TOKEN=your_github_token_here
```

For detailed testing information, see [tests/README.md](tests/README.md).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details 