#!/bin/sh

set -e  # Stop the script on any error

# Activate the virtual environment
. ./.venv/bin/activate

# Check if the virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment is NOT activated."
    exit 1
else
    echo "Virtual environment is activated: $VIRTUAL_ENV"
fi

# List installed packages
echo "Installed packages in the virtual environment:"
pip list

# Start the backend service (Gunicorn)
exec gunicorn -w 4 -b 0.0.0.0:5001 konduktor.dashboard.backend.main:app

