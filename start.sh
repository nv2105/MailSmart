#!/bin/bash
# --- MailSmart FastAPI Render Startup Script ---
set -e

# Create logs folder (optional)
mkdir -p logs

# Render provides a dynamic PORT variable
PORT=${PORT:-8000}

echo "🚀 Starting MailSmart FastAPI app on port $PORT..."

# Run FastAPI app
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
