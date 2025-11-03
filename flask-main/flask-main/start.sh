#!/bin/bash

# start.sh - Startup script for Flask app on Railway

# Exit on any error
set -e

# Install dependencies if requirements.txt exists
if [ -f requirements.txt ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install --no-cache-dir -r requirements.txt
fi

# Optional: Run database migrations (uncomment and customize if needed)
# if [ -f migrate.py ]; then
#     echo "Running migrations..."
#     python migrate.py
# fi

# Determine the port (Railway provides $PORT, fallback to 5000 for local testing)
PORT=${PORT:-5000}

# Start the Flask app
# Assumes your main file is app.py with `app = Flask(__name__)` and runs on host '0.0.0.0'
echo "Starting Flask app on port $PORT..."
gunicorn -b 0.0.0.0:$PORT app:app
