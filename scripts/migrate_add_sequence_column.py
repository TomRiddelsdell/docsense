#!/usr/bin/env python3
"""Migration script to add sequence column to events table."""
import asyncio
import asyncpg
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def migrate():
    """Add sequence column to events table."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return 1

    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)

    try:
        print("Adding sequence column to events table...")

        # Add sequence column
        await conn.execute("""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS sequence BIGSERIAL NOT NULL UNIQUE;
        """)
        print("✓ Added sequence column")

        # Create index for efficient querying
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_sequence ON events(sequence);
        """)
        print("✓ Created index on sequence column")

        # Backfill sequence for existing events (if any)
        print("Backfilling sequence for existing events...")
        result = await conn.execute("""
            WITH numbered_events AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (ORDER BY created_at, id) AS seq
                FROM events
                WHERE sequence IS NULL
            )
            UPDATE events e
            SET sequence = ne.seq
            FROM numbered_events ne
            WHERE e.id = ne.id
            AND e.sequence IS NULL;
        """)
        print(f"✓ Backfilled sequence: {result}")

        # Verify
        count = await conn.fetchval("SELECT COUNT(*) FROM events")
        print(f"✓ Total events in table: {count}")

        if count > 0:
            max_seq = await conn.fetchval("SELECT MAX(sequence) FROM events")
            print(f"✓ Maximum sequence value: {max_seq}")

        print("\n✅ Migration completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await conn.close()


if __name__ == "__main__":
    exit_code = asyncio.run(migrate())
    sys.exit(exit_code)
