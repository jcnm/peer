#!/bin/bash

# Test script for Piper installation
set -euo pipefail

# Import functions from install.sh
source /Users/smpceo/Desktop/peer/install.sh

# Set up basic variables needed by the install function
export SCRIPT_DIR="/Users/smpceo/Desktop/peer"
export VIRTUAL_ENV="/Users/smpceo/Desktop/peer/vepeer"
export FORCE_INSTALL=true

# Test the OS detection
detect_os

echo "=== Testing Piper Installation ==="
echo "OS: $OS"
echo "Script Dir: $SCRIPT_DIR"
echo "Virtual Env: $VIRTUAL_ENV"
echo ""

# Test the install_piper_tts function
if install_piper_tts; then
    echo "✅ Piper installation test passed"
    
    # Check if binary exists
    if [[ -x "$SCRIPT_DIR/piper/install/piper" ]]; then
        echo "✅ Piper binary found at: $SCRIPT_DIR/piper/install/piper"
        
        # Test basic functionality
        echo "Testing Piper binary..."
        if "$SCRIPT_DIR/piper/install/piper" --version; then
            echo "✅ Piper binary works"
        else
            echo "⚠️ Piper binary test failed"
        fi
    else
        echo "❌ Piper binary not found"
    fi
else
    echo "❌ Piper installation test failed"
fi
