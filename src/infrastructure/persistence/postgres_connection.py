"""PostgreSQL connection wrapper for dependency injection."""

import asyncpg


class PostgresConnection:
    """Wrapper for PostgreSQL connection pool for dependency injection."""

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize the connection wrapper.

        Args:
            pool: AsyncPG connection pool
        """
        self.pool = pool
