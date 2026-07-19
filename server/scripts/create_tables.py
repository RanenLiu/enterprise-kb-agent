"""Create all database tables from ORM models.

Idempotent — safe to run repeatedly. Models are auto-imported so
that SQLAlchemy's metadata collects all table definitions.

Usage:
    python -m scripts.create_tables
"""
from __future__ import annotations

import asyncio
import logging

from kb_adapter_postgres.base import Base
from kb_adapter_postgres.session import engine

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(level=logging.INFO)
    # Import all models so they register with Base.metadata
    import kb_biz.models  # noqa: F401
    try:
        import kb_enterprise.models  # noqa: F401 — may not exist in OS
    except ImportError:
        pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created")


if __name__ == "__main__":
    asyncio.run(main())
