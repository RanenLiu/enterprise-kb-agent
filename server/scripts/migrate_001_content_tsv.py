"""Migration 001: Add content_tsv column to chunks table for PG fulltext search.

Usage:
    python -m scripts.migrate_001_content_tsv

Run this after pulling the latest code to update existing databases.
New databases created via docker-entrypoint.sh will include this automatically
(since the Chunk model already has the content_tsv field).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from kb_adapter_postgres.session import engine

logger = logging.getLogger(__name__)


async def migrate():
    """Run add_content_tsv.sql directly via psql-compatible execution."""
    sql_path = Path(__file__).parent / "add_content_tsv.sql"
    sql = sql_path.read_text(encoding="utf-8")

    logger.info("Running migration 001: content_tsv (%s)", sql_path)
    async with engine.connect() as conn:
        await conn.exec_driver_sql(sql)
        await conn.commit()
    logger.info("Migration 001 complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(migrate())
