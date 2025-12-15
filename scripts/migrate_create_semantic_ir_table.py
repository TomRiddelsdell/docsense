#!/usr/bin/env python3
"""Migration script to create semantic_ir table."""
import asyncio
import asyncpg
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def migrate():
    """Create semantic_ir table."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return 1

    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)

    try:
        print("Creating semantic_ir table...")

        # Create semantic_ir table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_ir (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
                ir_type VARCHAR(50) NOT NULL,
                name VARCHAR(500),
                expression TEXT,
                variables JSONB,
                definition TEXT,
                term VARCHAR(500),
                context TEXT,
                table_data JSONB,
                row_count INTEGER,
                column_count INTEGER,
                target VARCHAR(500),
                reference_type VARCHAR(100),
                location TEXT,
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT semantic_ir_document_fk FOREIGN KEY (document_id)
                    REFERENCES document_views(id) ON DELETE CASCADE
            );
        """)
        print("✓ Created semantic_ir table")

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_ir_document_id
            ON semantic_ir(document_id);
        """)
        print("✓ Created index on document_id")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_ir_type
            ON semantic_ir(ir_type);
        """)
        print("✓ Created index on ir_type")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_ir_name
            ON semantic_ir(name) WHERE name IS NOT NULL;
        """)
        print("✓ Created index on name")

        # Verify
        count = await conn.fetchval("SELECT COUNT(*) FROM semantic_ir")
        print(f"✓ Total semantic_ir records: {count}")

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
