# BuildCheck Configuration Guide

This guide explains how to configure BuildCheck using the `config.yaml` file, with a focus on the new API optimization features.

## Quick Start

1. Create a configuration file:
```bash
python build_check.py --create-config
```

2. Edit `config.yaml` with your settings
3. Verify your configuration:
```bash
python build_check.py --show-config
```

4. Run BuildCheck:
```bash
python build_check.py
```

## Configuration Structure

The `config.yaml` file is organized into several sections:

### Basic Configuration
```yaml
# GitHub Organization Configuration
organization: "your-org-name"  # Required: GitHub organization to analyze
```

### API Optimization Settings (NEW!)

The new API optimization section provides advanced control over API usage and performance:

```yaml
api_optimization:
  # API Call Prediction
  predict_api_calls: true      # Predict API call usage before analysis
  prediction_warning_threshold: 3000  # Warn if predicted calls exceed this number
  
  # Bulk Analysis Features
  bulk_analysis: true          # Use bulk file fetching to reduce API calls
  bulk_file_limit: 10          # Maximum files to fetch in bulk per repository
  
  # Smart Rate Limiting
  adaptive_rate_limiting: true # Adjust delays based on rate limit status
  conservative_mode: false     # Use more conservative rate limiting for large orgs
  
  # API Call Reduction Strategies
  strategies:
    jenkins_only: true         # Only analyze repositories with Jenkinsfiles
    skip_archived: true        # Skip archived repositories
    skip_forks: false          # Skip forked repositories (set to true to reduce calls)
    max_repositories: null     # Limit total repositories analyzed (null = no limit)
```

## API Optimization Features Explained

### Cache-Aware API Prediction (NEW!)

The API optimization now intelligently considers cache availability when making predictions:

**How it works**:
- **With cache**: Uses actual cached repository count, shows 0 discovery calls
- **Without cache**: Uses estimated repository count, includes discovery calls
- **Smart recommendations**: Provides different advice based on cache status

**Benefits**:
- **Accurate predictions**: No more over-estimating when cache is available
- **Better planning**: Know exactly how many API calls will be made
- **Cache encouragement**: Shows the benefits of enabling caching
- **Rate limit safety**: More accurate rate limit impact assessment

### 1. API Call Prediction

**Purpose**: Predict how many API calls your analysis will make before starting, taking into account cache availability.

**Settings**:
- `predict_api_calls`: Enable/disable prediction
- `prediction_warning_threshold`: Number of calls that triggers a warning

**Example**:
```yaml
api_optimization:
  predict_api_calls: true
  prediction_warning_threshold: 3000  # Warn if > 3000 calls predicted
```

**Output with Cache Available**:
```
API Call Prediction:
Total Repositories: 1000
Repositories to Analyze: 50
Discovery API Calls: 0
Total Estimated API Calls: 500
Rate Limit Impact: safe

Cache Status:
Cache Available: ✅ Yes
Cached Repositories: 50
```

**Output without Cache**:
```
API Call Prediction:
Total Repositories: 1000
Repositories to Analyze: 300
Discovery API Calls: 1
Total Estimated API Calls: 3001
Rate Limit Impact: exceeded

Cache Status:
Cache Available: ❌ No
```

**Key Benefits**:
- **Cache-aware predictions**: Shows different estimates based on cache availability
- **Accurate repository counts**: Uses actual cached repository count when available
- **Discovery call reduction**: Shows 0 discovery calls when cache is available
- **Smart recommendations**: Provides cache-specific optimization advice

**Practical Example**:
```bash
# First run (no cache) - shows higher estimates
python build_check.py --org my-org --predict-api --use-cache
# Output: 3001 API calls estimated, rate limit impact: exceeded

# After running analysis (cache populated)
python build_check.py --org my-org --predict-api --use-cache  
# Output: 500 API calls estimated, rate limit impact: safe
```

### 2. Bulk Analysis

**Purpose**: Fetch multiple files in a single API call to reduce total calls.

**Settings**:
- `bulk_analysis`: Enable/disable bulk fetching
- `bulk_file_limit`: Maximum files per bulk request

**Example**:
```yaml
api_optimization:
  bulk_analysis: true
  bulk_file_limit: 15  # Fetch up to 15 files per API call
```

**Benefits**:
- Reduces API calls by 60-80% for large organizations
- Faster analysis completion
- Lower risk of hitting rate limits

### 3. Smart Rate Limiting

**Purpose**: Automatically adjust API call timing based on rate limit status.

**Settings**:
- `adaptive_rate_limiting`: Enable adaptive delays
- `conservative_mode`: Use more conservative timing for large orgs

**Example**:
```yaml
api_optimization:
  adaptive_rate_limiting: true
  conservative_mode: true  # For organizations with 1000+ repositories
```

### 4. API Call Reduction Strategies

**Purpose**: Skip repositories that are unlikely to contain build tools.

**Settings**:
```yaml
strategies:
  jenkins_only: true      # Only repos with Jenkinsfiles
  skip_archived: true     # Skip archived repositories
  skip_forks: false       # Skip forked repositories
  max_repositories: 500   # Limit total repos analyzed
```

## Configuration Examples

### Example 1: Large Organization (1000+ repos)
```yaml
organization: "large-enterprise-org"

api_optimization:
  predict_api_calls: true
  prediction_warning_threshold: 5000
  bulk_analysis: true
  bulk_file_limit: 20
  adaptive_rate_limiting: true
  conservative_mode: true
  strategies:
    jenkins_only: true
    skip_archived: true
    skip_forks: true
    max_repositories: 1000

parallelism:
  max_workers: 4  # Reduced for large orgs
  rate_limit_delay: 0.1  # More conservative
```

### Example 2: Small Organization (< 100 repos)
```yaml
organization: "small-dev-team"

api_optimization:
  predict_api_calls: true
  prediction_warning_threshold: 1000
  bulk_analysis: false  # Not needed for small orgs
  adaptive_rate_limiting: true
  conservative_mode: false
  strategies:
    jenkins_only: false  # Analyze all repos
    skip_archived: true
    skip_forks: false

parallelism:
  max_workers: 8
  rate_limit_delay: 0.05
```

### Example 3: Jenkins-Only Analysis
```yaml
organization: "ci-cd-focused-org"

api_optimization:
  predict_api_calls: true
  prediction_warning_threshold: 2000
  bulk_analysis: true
  bulk_file_limit: 10
  strategies:
    jenkins_only: true
    skip_archived: true
    skip_forks: false

analysis:
  jenkins_only: true  # Also set in analysis section
```

## Performance Settings

### Parallelism Configuration
```yaml
parallelism:
  max_workers: 8               # Number of parallel workers (1-16)
  rate_limit_delay: 0.05       # Delay between API calls in seconds
  optimized: true              # Use optimized mode for large organizations
```

**Recommendations**:
- **Small orgs (< 100 repos)**: `max_workers: 8`, `rate_limit_delay: 0.05`
- **Medium orgs (100-500 repos)**: `max_workers: 6`, `rate_limit_delay: 0.05`
- **Large orgs (500+ repos)**: `max_workers: 4`, `rate_limit_delay: 0.1`

## Repository Exclusions

Exclude repositories that don't need analysis:

```yaml
exclusions:
  # Exact repository names
  repositories:
    - "infrastructure-environments"
    - "documentation"
    - "wiki-content"
  
  # Pattern-based exclusions
  patterns:
    - "terraform-*"     # All terraform repos
    - "*-infra"         # All infrastructure repos
    - "legacy-*"        # All legacy repos
    - "test-*"          # All test repos
```

## Caching Configuration

```yaml
caching:
  enabled: true                # Enable caching
  directory: ".cache"          # Cache directory
  duration: 7200               # Cache duration in seconds (2 hours)
```

## Output Configuration

```yaml
output:
  json_report: "report.json"   # JSON output file
  csv_report: "report.csv"     # CSV output file
  html_report: "report.html"   # HTML output file
  verbose: false               # Enable verbose logging
```

## Best Practices

### 1. Start Conservative
For new organizations, start with conservative settings:
```yaml
api_optimization:
  predict_api_calls: true
  prediction_warning_threshold: 2000
  bulk_analysis: true
  conservative_mode: true
  strategies:
    jenkins_only: true
    skip_archived: true
```

### 2. Monitor API Usage
Always enable API prediction to monitor usage:
```yaml
api_optimization:
  predict_api_calls: true
  prediction_warning_threshold: 3000
```

### 3. Use Appropriate Parallelism
Match parallelism to organization size:
- Small orgs: `max_workers: 8`
- Medium orgs: `max_workers: 6`
- Large orgs: `max_workers: 4`

### 4. Enable Caching
Always enable caching for development:
```yaml
caching:
  enabled: true
  duration: 7200  # 2 hours
```

## Troubleshooting

### Rate Limit Issues
If you're hitting rate limits:
1. Increase `rate_limit_delay`
2. Reduce `max_workers`
3. Enable `conservative_mode`
4. Use `jenkins_only: true`

### Slow Performance
If analysis is too slow:
1. Increase `max_workers` (if rate limits allow)
2. Enable `bulk_analysis`
3. Use `jenkins_only: true`
4. Add more repository exclusions

### Configuration Errors
Common issues:
- Missing `organization` field
- Invalid YAML syntax
- Non-existent configuration file

## Command Line Override

You can override configuration settings with command line options:

```bash
# Override organization
python build_check.py --org "different-org"

# Override API optimization
python build_check.py --predict-api --bulk-analysis

# Override parallelism
python build_check.py --max-workers 4 --rate-limit-delay 0.1
```

## Configuration Verification

Use the `--show-config` option to see exactly how your configuration is being interpreted:

```bash
# Show current configuration
python build_check.py --show-config

# Show configuration with overrides
python build_check.py --show-config --org "test-org" --max-workers 4

# Show configuration without config file
python build_check.py --show-config --config nonexistent.yaml
```

This is useful for:
- Debugging configuration issues
- Understanding how command-line overrides work
- Verifying settings before running analysis
- Troubleshooting configuration problems

## Migration from Old Configuration

If you have an existing `config.yaml` file, the new API optimization section will be added automatically when you run:

```bash
python build_check.py --create-config
```

This will preserve your existing settings and add the new API optimization options with sensible defaults. 