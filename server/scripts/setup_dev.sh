#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up development environment ==="

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$SCRIPT_DIR"
pip install -e packages/kb-core -e packages/kb-biz -e packages/kb-adapter-postgres -e packages/kb-adapter-rabbitmq
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic pydantic-settings pyjwt passlib[bcrypt] python-multipart redis httpx jieba minio openpyxl

# Start Docker services (PostgreSQL, Redis, etc.)
echo "Starting infrastructure services..."
docker compose up -d postgres redis minio etcd milvus

echo ""
echo "=== Setup complete ==="
echo "Start backend (dev):   cd server && uvicorn backend.main:app --reload"
echo "Start frontend (dev):  cd frontend && npm install && npm run dev"
echo ""
echo "Default admin:         admin / admin123"
echo ""
