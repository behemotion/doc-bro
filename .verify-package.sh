#!/bin/bash
# Script to verify package installation includes all required files
# Run this after making changes to ensure package builds correctly

set -e

echo "🔍 Verifying package installation integrity..."

# Clean cache and reinstall
echo "Cleaning UV cache..."
uv cache clean > /dev/null 2>&1

echo "Reinstalling package..."
uv tool uninstall docbro > /dev/null 2>&1 || true
uv tool install . --force --reinstall > /dev/null 2>&1

# Test critical imports
echo "Testing critical imports..."
cd /Users/alexandr/.local/share/uv/tools/docbro/lib/python3.13/site-packages

# Test each critical model import
python -c "from src.models import SetupSession; print('✓ SetupSession')" 2>/dev/null
python -c "from src.models import Project; print('✓ Project')" 2>/dev/null
python -c "from src.models import InstallationContext; print('✓ InstallationContext')" 2>/dev/null

# Test docbro command works
echo "Testing docbro command..."
docbro --help > /dev/null 2>&1 && echo "✓ docbro command"

echo "✅ Package installation verified successfully!"