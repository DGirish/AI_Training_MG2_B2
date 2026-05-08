#!/usr/bin/env python3
"""
Execute migration SQL file against Supabase database
"""
import os
import asyncio
from pathlib import Path
from urllib.parse import urlparse

import asyncpg


async def run_migration():
    # Load environment
    env_path = Path(__file__).parent / ".env"
    env_vars = {}
    
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    database_url = env_vars.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in .env")
        return False
    
    # Parse database URL
    parsed = urlparse(database_url)
    
    # Create connection
    try:
        conn = await asyncpg.connect(
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
            host=parsed.hostname,
            port=parsed.port or 5432,
        )
        print(f"✓ Connected to {parsed.hostname}:{parsed.port or 5432}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False
    
    # Read and execute migration
    migration_file = Path(__file__).parent / "backend" / "db" / "migrate_generated_images.sql"
    
    try:
        with open(migration_file, "r") as f:
            migration_sql = f.read()
        
        print(f"\n📄 Executing migration from {migration_file.name}...")
        
        # Execute the entire migration as a single transaction
        result = await conn.execute(migration_sql)
        print(f"  ✓ Migration executed: {result}")
        
        print("\n✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
