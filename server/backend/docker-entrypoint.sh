#!/bin/sh
set -e

cd /app

echo "=== Creating tables ==="
python -c "
from kb_adapter_postgres.base import Base
from kb_adapter_postgres.session import engine
# Import all models so SQLAlchemy knows about them
import kb_biz.models  # noqa: F401
import asyncio
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
print('Tables created')
"

echo "=== Seeding database ==="
python -m scripts.seed_os

echo "=== Starting API server ==="
exec uvicorn main:app --host 0.0.0.0 --port 8000
