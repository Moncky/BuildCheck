# BuildCheck API Optimization Guide

This guide explains the new API optimization features in BuildCheck that help reduce GitHub API calls and provide better insights into analysis requirements.

## Overview

BuildCheck now includes advanced API optimization capabilities that can:

1. **Predict API usage** before starting analysis
2. **Reduce API calls by up to 80%** using bulk file fetching
3. **Optimize file check order** based on success rates
4. **Provide rate limit impact assessment**
5. **Suggest optimizations** for large organizations

## New Features

### 1. API Call Prediction

Predict the number of API calls needed before starting analysis:

```bash
# Predict API usage for full analysis
python build_check.py --org your-org --predict-api

# Predict API usage for Jenkins-only mode
python build_check.py --org your-org --jenkins-only --predict-api
```

**Example Output:**
```
API Call Prediction
┌─────────────────────────┬─────────┬─────────────────────────┐
│ Metric                  │ Value   │ Details                 │
├─────────────────────────┼─────────┼─────────────────────────┤
│ Total Repositories      │ 500     │                         │
│ Repositories to Analyze │ 400     │                         │
│ Discovery API Calls     │ 5       │                         │
│ API Calls per Repository│ 10      │                         │
│ Total Estimated API Calls│ 4005   │                         │
│ Time Estimate           │ 3.3 minutes │                     │
│ Rate Limit Impact       │ safe    │ green                   │
└─────────────────────────┴─────────┴─────────────────────────┘

Recommendations:
  • Enable caching for better performance
```

### 2. Bulk Analysis Mode

Use bulk file fetching to dramatically reduce API calls:

```bash
# Use bulk analysis for better efficiency
python build_check.py --org your-org --bulk-analysis

# Combine with other optimizations
python build_check.py --org your-org --jenkins-only --bulk-analysis --predict-api
```

**Benefits:**
- Reduces API calls by 80% for large organizations
- Fetches all file contents in parallel
- Optimizes file check order based on success rates

### 3. Organization Size Estimation

Quickly estimate organization size without full enumeration:

```python
from api_optimizer import APIOptimizer

optimizer = APIOptimizer(github, org_name)
estimated_size = optimizer.get_organization_size_estimate()
print(f"Estimated repositories: {estimated_size}")
```

### 4. Rate Limit Impact Assessment

Automatically assess whether analysis will exceed rate limits:

- **Safe**: Analysis uses < 50% of available API calls
- **Moderate**: Analysis uses 50-80% of available API calls
- **Risky**: Analysis uses 80-100% of available API calls
- **Exceeded**: Analysis will exceed available API calls

## API Call Reduction Strategies

### Strategy 1: Jenkins-Only Mode (70% reduction)

Only analyze repositories that contain Jenkinsfiles:

```bash
python build_check.py --org your-org --jenkins-only
```

**When to use:**
- You only care about CI/CD repositories
- Organization has many non-Java repositories
- You want to focus on build automation

### Strategy 2: Bulk File Fetching (80% reduction)

Fetch all file contents in a single operation:

```bash
python build_check.py --org your-org --bulk-analysis
```

**When to use:**
- Organization has 50+ repositories
- You want maximum API efficiency
- You have sufficient memory for bulk operations

### Strategy 3: Aggressive Caching

Cache repository lists and reuse them:

```bash
python build_check.py --org your-org --use-cache
```

**When to use:**
- Running analysis multiple times
- Testing different configurations
- Development and debugging

### Strategy 4: Optimized File Check Order

Check most likely files first to reduce unnecessary API calls:

The system automatically optimizes file check order based on success rates:

1. `.mvn/wrapper/maven-wrapper.properties` (80% success rate)
2. `gradle/wrapper/gradle-wrapper.properties` (80% success rate)
3. `pom.xml` (60% success rate)
4. `build.gradle` (60% success rate)
5. `Jenkinsfile` (40% success rate)
6. `gradle.properties` (30% success rate)

## Alternative API Endpoints

The system can use different GitHub API endpoints for better efficiency:

| Endpoint | Use Case | Benefits |
|----------|----------|----------|
| **Search API** | Finding repositories with specific files | Efficient for targeted searches |
| **Contents API** | Standard file content access | Reliable, used by default |
| **GraphQL API** | Complex queries | Can fetch multiple resources in one call |
| **Trees API** | Directory structure | Can fetch entire trees in one call |
| **Blobs API** | Direct file access | Efficient for known file SHAs |

## Performance Comparison

| Mode | API Calls | Time | Use Case |
|------|-----------|------|----------|
| **Full Analysis** | ~10 per repo | Slow | Complete analysis |
| **Jenkins-Only** | ~3 per repo | Fast | CI/CD focus |
| **Bulk Analysis** | ~2 per repo | Very Fast | Large organizations |
| **Cached** | ~1 per repo | Instant | Repeated runs |

## Configuration Options

### Command Line Options

```bash
# API prediction
--predict-api              # Show API usage predictions

# Bulk analysis
--bulk-analysis            # Use bulk file fetching

# Rate limiting
--rate-limit-delay 0.05    # Delay between API calls (seconds)
--max-workers 4            # Number of parallel workers

# Caching
--use-cache                # Enable caching
--cache-dir .cache         # Cache directory
--clear-cache              # Clear cache before running
```

### Configuration File

```yaml
# config.yaml
parallelism:
  max_workers: 4               # Reduced for better API efficiency
  rate_limit_delay: 0.05       # Conservative rate limiting
  optimized: true              # Use optimized mode

caching:
  enabled: true                # Always enable caching
  duration: 7200               # Cache for 2 hours

analysis:
  jenkins_only: true          # Use Jenkins-only mode
  bulk_analysis: true         # Use bulk file fetching
```

## Best Practices

### For Large Organizations (500+ repos)

1. **Always use prediction first:**
   ```bash
   python build_check.py --org your-org --predict-api
   ```

2. **Use Jenkins-only mode:**
   ```bash
   python build_check.py --org your-org --jenkins-only --bulk-analysis
   ```

3. **Enable aggressive caching:**
   ```bash
   python build_check.py --org your-org --use-cache --cache-dir .cache
   ```

4. **Reduce parallel workers:**
   ```bash
   python build_check.py --org your-org --max-workers 4
   ```

### For Development and Testing

1. **Use caching for repeated runs:**
   ```bash
   python build_check.py --org your-org --use-cache
   ```

2. **Test with single repository first:**
   ```bash
   python build_check.py --org your-org --repo test-repo
   ```

3. **Use verbose mode for debugging:**
   ```bash
   python build_check.py --org your-org --verbose
   ```

## Troubleshooting

### Rate Limit Issues

If you're hitting rate limits:

1. **Check current usage:**
   ```bash
   python build_check.py --org your-org --predict-api
   ```

2. **Use more conservative settings:**
   ```bash
   python build_check.py --org your-org --rate-limit-delay 0.1 --max-workers 2
   ```

3. **Split analysis into sessions:**
   ```bash
   # First session: Jenkins repositories
   python build_check.py --org your-org --jenkins-only
   
   # Second session: Remaining repositories
   python build_check.py --org your-org --repo-pattern "java-*"
   ```

### Memory Issues

If you encounter memory issues with bulk analysis:

1. **Reduce batch size:**
   ```bash
   python build_check.py --org your-org --max-workers 2
   ```

2. **Use individual analysis:**
   ```bash
   # Don't use --bulk-analysis flag
   python build_check.py --org your-org
   ```

## Demo Script

Run the demo to see all features in action:

```bash
python demo_api_optimization.py --org your-org --token your-token
```

This will show:
- Organization size estimation
- API call predictions for different modes
- Alternative API endpoints
- Optimization suggestions
- File pattern optimization
- Analysis plan creation

## Migration Guide

### From Old Version

If you're upgrading from an older version:

1. **No breaking changes** - all existing commands still work
2. **New features are opt-in** - use new flags to enable optimizations
3. **Backward compatible** - existing scripts continue to work

### Recommended Migration Steps

1. **Test with prediction first:**
   ```bash
   python build_check.py --org your-org --predict-api
   ```

2. **Enable caching:**
   ```bash
   python build_check.py --org your-org --use-cache
   ```

3. **Try bulk analysis:**
   ```bash
   python build_check.py --org your-org --bulk-analysis
   ```

4. **Update configuration:**
   ```yaml
   # Add to your config.yaml
   parallelism:
     optimized: true
   analysis:
     bulk_analysis: true
   ```

## Support

For issues or questions about API optimization:

1. **Check the demo script** for examples
2. **Use --verbose flag** for detailed logging
3. **Run with --predict-api** to understand API usage
4. **Review this guide** for best practices

The API optimization features are designed to make BuildCheck more efficient and user-friendly for large organizations while maintaining the same accuracy and reliability. 