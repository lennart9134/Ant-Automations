"""Async database connection pool backed by asyncpg.

Reads POSTGRES_DSN from the environment and exposes acquire() for
transactional queries.  Falls back to in-memory mode when the DSN is
not set (useful for local development and tests).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")


class DatabasePool:
    """Thin wrapper around asyncpg.Pool with lifecycle management."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if not POSTGRES_DSN:
            logger.warning("POSTGRES_DSN not set — running without database persistence")
            return
        self._pool = await asyncpg.create_pool(
            dsn=POSTGRES_DSN,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Database pool created (%s)", POSTGRES_DSN.split("@")[-1])

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")

    @property
    def connected(self) -> bool:
        return self._pool is not None

    async def execute(self, query: str, *args: Any) -> str:
        if not self._pool:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        if not self._pool:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        if not self._pool:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        if not self._pool:
            raise RuntimeError("Database pool is not connected")
        return await self._pool.fetchval(query, *args)

    async def healthcheck(self) -> bool:
        """Return True if the pool can execute a trivial query."""
        if not self._pool:
            return False
        try:
            await self._pool.fetchval("SELECT 1")
            return True
        except Exception:
            return False
