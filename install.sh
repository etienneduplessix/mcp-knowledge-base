#!/bin/bash

# Installation script for MCP Knowledge Base Server

set -e

echo "=== MCP Knowledge Base Server Setup ==="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "Error: Python 3.10 or higher is required (found $python_version)"
    exit 1
fi

echo "✓ Python version check passed: $python_version"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed"
    exit 1
fi

echo "✓ pip3 is available"

# Install dependencies
echo
echo "Installing dependencies..."
pip3 install -r requirements.txt

echo
echo "✓ Dependencies installed successfully"

# Create directories if they don't exist
echo
echo "Creating knowledge base directories..."
mkdir -p knowledge docs config

echo "✓ Directories created"

# Set up environment variables
echo
echo "Setting up environment..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create .env file for local development
cat > .env << EOF
# MCP Knowledge Base Server Configuration
KB_PATHS=$SCRIPT_DIR/knowledge,$SCRIPT_DIR/docs,$SCRIPT_DIR/config
KB_EXTENSIONS=.md,.json
KB_MAX_SIZE_MB=10
EOF

echo "✓ Environment configuration saved to .env"

echo
echo "=== Installation Complete ==="
echo
echo "To run the server:"
echo "  python3 mcp_kb_server.py"
echo
echo "To add to Claude Desktop:"
echo "  1. Open Claude Desktop"
echo "  2. Go to Settings → Developer → Edit Config"
echo "  3. Copy the configuration from claude-desktop-config.json"
echo "  4. Update the paths to: $SCRIPT_DIR"
echo
echo "Knowledge base directories:"
echo "  - $SCRIPT_DIR/knowledge"
echo "  - $SCRIPT_DIR/docs"
echo "  - $SCRIPT_DIR/config"
echo
echo "Add your markdown and JSON files to these directories!"
