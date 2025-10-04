#!/bin/bash
# start.sh for Render deployment
# Runs MailSmart FastAPI app with Gunicorn

# optional: print environment variables for debug
echo "LOG_DIR=$LOG_DIR"
echo "GOOGLE_CLIENT_SECRET_FILE=$GOOGLE_CLIENT_SECRET_FILE"
echo "GOOGLE_TOKEN_FILE=$GOOGLE_TOKEN_FILE"

# start app
exec gunicorn app.main:app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120
