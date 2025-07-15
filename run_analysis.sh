#!/bin/bash

# BuildCheck Analysis Script
# This script runs the GitHub organization analysis

set -e

echo "🚀 Starting BuildCheck Analysis..."

# Check if GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Error: GITHUB_TOKEN environment variable is not set"
    echo "Please set your GitHub personal access token:"
    echo "export GITHUB_TOKEN=your_token_here"
    exit 1
fi

# Check if organization name is provided
if [ -z "$1" ]; then
    echo "❌ Error: Organization name is required"
    echo "Usage: ./run_analysis.sh <organization_name> [jenkins-only] [max-workers] [use-cache]"
    echo ""
    echo "Options:"
    echo "  jenkins-only    Only analyze repositories with Jenkinsfiles (much faster)"
    echo "  max-workers     Number of parallel workers (default: 4, max: 8)"
    echo "  use-cache       Enable caching to reduce API calls during development"
    exit 1
fi

ORG_NAME="$1"
JENKINS_ONLY=""
MAX_WORKERS=""
USE_CACHE=""

# Check if jenkins-only flag is provided
if [ "$2" = "jenkins-only" ]; then
    JENKINS_ONLY="--jenkins-only"
    echo "🚀 Using Jenkins-only mode (fast analysis)"
    
    # Check for max-workers as third parameter
    if [ -n "$3" ]; then
        if [ "$3" = "use-cache" ]; then
            USE_CACHE="--use-cache"
            echo "💾 Using cache mode (reduces API calls)"
        else
            MAX_WORKERS="--max-workers $3"
            echo "⚡ Using $3 parallel workers"
            
            # Check for use-cache as fourth parameter
            if [ -n "$4" ] && [ "$4" = "use-cache" ]; then
                USE_CACHE="--use-cache"
                echo "💾 Using cache mode (reduces API calls)"
            fi
        fi
    fi
else
    # Check for max-workers as second parameter
    if [ -n "$2" ]; then
        if [ "$2" = "use-cache" ]; then
            USE_CACHE="--use-cache"
            echo "💾 Using cache mode (reduces API calls)"
        else
            MAX_WORKERS="--max-workers $2"
            echo "⚡ Using $2 parallel workers"
            
            # Check for use-cache as third parameter
            if [ -n "$3" ] && [ "$3" = "use-cache" ]; then
                USE_CACHE="--use-cache"
                echo "💾 Using cache mode (reduces API calls)"
            fi
        fi
    fi
fi

OUTPUT_FILE="build_check_report_$(date +%Y%m%d_%H%M%S).json"

echo "📊 Analyzing organization: $ORG_NAME"
echo "📁 Output will be saved to: $OUTPUT_FILE"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Run the analysis
python build_check.py --org "$ORG_NAME" --output "$OUTPUT_FILE" $JENKINS_ONLY $MAX_WORKERS $USE_CACHE

echo "✅ Analysis complete!"
echo "📄 Report saved to: $OUTPUT_FILE" 