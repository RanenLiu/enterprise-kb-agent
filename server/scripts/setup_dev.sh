#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up development environment ==="

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$SCRIPT_DIR"
uv sync || pip install -r backend/requirements.txt

# Run database migrations
echo "Running database migrations..."
cd "$SCRIPT_DIR/backend"
PYTHONPATH=. alembic upgrade head

# Seed data
echo "Seeding initial data..."
PYTHONPATH=. python scripts/seed_data.py

echo ""
echo "=== Setup complete ==="
echo "Start services:        docker compose up -d"
echo "Start backend (dev):   cd backend && PYTHONPATH=. uvicorn app.main:app --reload"
echo "Start frontend (dev):  cd frontend && npm install && npm run dev"
echo ""
echo "Default super admin:   admin / admin123"
echo "Register new tenant:   visit /register to create a tenant admin account"
echo ""
