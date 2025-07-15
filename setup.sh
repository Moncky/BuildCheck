#!/bin/bash

# BuildCheck Setup Script
# This script sets up the virtual environment and installs dependencies

set -e

echo "🚀 Setting up BuildCheck environment..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

# Check if virtualenv is available
if ! command -v virtualenv &> /dev/null; then
    echo "📦 Installing virtualenv..."
    pip3 install virtualenv
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    virtualenv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment manually:"
echo "source venv/bin/activate"
echo ""
echo "To run the analysis:"
echo "python build_check.py --org your-organization-name"
echo ""
echo "Or use the shell script:"
echo "./run_analysis.sh your-organization-name" 