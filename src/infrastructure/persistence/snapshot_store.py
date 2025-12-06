from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID
import json

import asyncpg


@dataclass
class Snapshot:
    aggregate_id: UUID
    aggregate_type: str
    version: int
    state: Dict[str, Any]


class SnapshotStore(ABC):
    @abstractmethod
    async def save(self, snapshot: Snapshot) -> None:
        pass

    @abstractmethod
    async def get(self, aggregate_id: UUID) -> Optional[Snapshot]:
        pass

    @abstractmethod
    async def delete(self, aggregate_id: UUID) -> None:
        pass


class PostgresSnapshotStore(SnapshotStore):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def save(self, snapshot: Snapshot) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO snapshots (aggregate_id, aggregate_type, version, state)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (aggregate_id, version)
                DO UPDATE SET state = $4
                """,
                snapshot.aggregate_id,
                snapshot.aggregate_type,
                snapshot.version,
                json.dumps(snapshot.state)
            )

    async def get(self, aggregate_id: UUID) -> Optional[Snapshot]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT aggregate_id, aggregate_type, version, state
                FROM snapshots
                WHERE aggregate_id = $1
                ORDER BY version DESC
                LIMIT 1
                """,
                aggregate_id
            )

        if row is None:
            return None

        state = json.loads(row["state"]) if isinstance(row["state"], str) else row["state"]
        return Snapshot(
            aggregate_id=row["aggregate_id"],
            aggregate_type=row["aggregate_type"],
            version=row["version"],
            state=state
        )

    async def delete(self, aggregate_id: UUID) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM snapshots WHERE aggregate_id = $1",
                aggregate_id
            )


class InMemorySnapshotStore(SnapshotStore):
    def __init__(self):
        self._snapshots: Dict[UUID, Snapshot] = {}

    async def save(self, snapshot: Snapshot) -> None:
        self._snapshots[snapshot.aggregate_id] = snapshot

    async def get(self, aggregate_id: UUID) -> Optional[Snapshot]:
        return self._snapshots.get(aggregate_id)

    async def delete(self, aggregate_id: UUID) -> None:
        self._snapshots.pop(aggregate_id, None)

    def clear(self) -> None:
        self._snapshots.clear()
