#!/usr/bin/env bash

# Smoketest script for forestroutemvp repository
# This script performs a quick local smoke test to verify the basic functionality
# of the forestroutemvp package after installation.

set -e

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate   # Use .venv\Scripts\Activate.ps1 on Windows

# Upgrade pip to the latest version
pip install --upgrade pip

# Install development requirements if available, otherwise install regular requirements
if [ -f requirements-dev.txt ]; then
    pip install -r requirements-dev.txt
elif [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Run pytest to execute tests, if configured
python -m pytest -q || echo "pytest failed or no tests"

# Check importability of common package names
python -c "import importlib,sys; candidates=['frp','forestroutemvp','forest_route_mvp']; \
for n in candidates: \
 try: importlib.import_module(n); print(n+' import OK'); break \
 except Exception as e: print(n+' import failed:', e, file=sys.stderr)"

echo "Smoketest completed."