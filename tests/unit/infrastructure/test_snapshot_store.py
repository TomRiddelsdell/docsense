import pytest
from uuid import uuid4

from src.infrastructure.persistence.snapshot_store import (
    InMemorySnapshotStore,
    Snapshot,
)


class TestInMemorySnapshotStore:
    @pytest.fixture
    def store(self):
        return InMemorySnapshotStore()

    @pytest.fixture
    def sample_snapshot(self):
        return Snapshot(
            aggregate_id=uuid4(),
            aggregate_type="Document",
            version=10,
            state={
                "filename": "test.pdf",
                "status": "converted",
                "sections": []
            }
        )

    @pytest.mark.asyncio
    async def test_save_and_get_snapshot(self, store, sample_snapshot):
        await store.save(sample_snapshot)
        
        retrieved = await store.get(sample_snapshot.aggregate_id)
        
        assert retrieved is not None
        assert retrieved.aggregate_id == sample_snapshot.aggregate_id
        assert retrieved.version == 10
        assert retrieved.state["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_unknown_aggregate(self, store):
        result = await store.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_save_overwrites_existing_snapshot(self, store):
        aggregate_id = uuid4()
        
        snapshot1 = Snapshot(
            aggregate_id=aggregate_id,
            aggregate_type="Document",
            version=5,
            state={"status": "uploaded"}
        )
        await store.save(snapshot1)
        
        snapshot2 = Snapshot(
            aggregate_id=aggregate_id,
            aggregate_type="Document",
            version=10,
            state={"status": "analyzed"}
        )
        await store.save(snapshot2)
        
        retrieved = await store.get(aggregate_id)
        assert retrieved.version == 10
        assert retrieved.state["status"] == "analyzed"

    @pytest.mark.asyncio
    async def test_delete_snapshot(self, store, sample_snapshot):
        await store.save(sample_snapshot)
        
        await store.delete(sample_snapshot.aggregate_id)
        
        result = await store.get(sample_snapshot.aggregate_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_snapshot_does_not_raise(self, store):
        await store.delete(uuid4())

    @pytest.mark.asyncio
    async def test_clear(self, store, sample_snapshot):
        await store.save(sample_snapshot)
        
        another = Snapshot(
            aggregate_id=uuid4(),
            aggregate_type="PolicyRepository",
            version=5,
            state={"name": "Test"}
        )
        await store.save(another)
        
        store.clear()
        
        assert await store.get(sample_snapshot.aggregate_id) is None
        assert await store.get(another.aggregate_id) is None


class TestSnapshot:
    def test_snapshot_creation(self):
        aggregate_id = uuid4()
        snapshot = Snapshot(
            aggregate_id=aggregate_id,
            aggregate_type="Document",
            version=5,
            state={"key": "value"}
        )
        
        assert snapshot.aggregate_id == aggregate_id
        assert snapshot.aggregate_type == "Document"
        assert snapshot.version == 5
        assert snapshot.state == {"key": "value"}

    def test_snapshot_with_complex_state(self):
        snapshot = Snapshot(
            aggregate_id=uuid4(),
            aggregate_type="Document",
            version=10,
            state={
                "nested": {
                    "deep": {
                        "value": 123
                    }
                },
                "list": [1, 2, 3],
                "mixed": [{"a": 1}, {"b": 2}]
            }
        )
        
        assert snapshot.state["nested"]["deep"]["value"] == 123
        assert snapshot.state["list"] == [1, 2, 3]
