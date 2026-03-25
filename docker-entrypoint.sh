#!/bin/sh
set -e

echo "Running startup checks..."
python3 scripts/startup.py

echo "Starting server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}"
