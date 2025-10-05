#!/usr/bin/env bash
set -o errexit  # stop on error

echo "🚀 Starting MailSmart FastAPI app on Render..."

# Render provides a dynamic $PORT environment variable
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
