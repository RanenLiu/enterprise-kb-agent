#!/bin/sh
set -e

cd /app

echo "=== Creating tables ==="
python -m scripts.create_tables

echo "=== Seeding database ==="
python -m scripts.seed_os

echo "=== Starting API server ==="
exec uvicorn main:app --host 0.0.0.0 --port 8000
