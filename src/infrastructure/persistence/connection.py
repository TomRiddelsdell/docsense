import os
from typing import Optional
import asyncpg


class DatabaseConnection:
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise RuntimeError("DATABASE_URL environment variable is not set")
            cls._pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
        return cls._pool

    @classmethod
    async def close(cls) -> None:
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None

    @classmethod
    async def execute(cls, query: str, *args) -> str:
        pool = await cls.get_pool()
        return await pool.execute(query, *args)

    @classmethod
    async def fetch(cls, query: str, *args) -> list:
        pool = await cls.get_pool()
        return await pool.fetch(query, *args)

    @classmethod
    async def fetchrow(cls, query: str, *args) -> Optional[asyncpg.Record]:
        pool = await cls.get_pool()
        return await pool.fetchrow(query, *args)

    @classmethod
    async def fetchval(cls, query: str, *args):
        pool = await cls.get_pool()
        return await pool.fetchval(query, *args)
