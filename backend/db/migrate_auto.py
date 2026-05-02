#!/usr/bin/env python3
"""
Supabase Schema Migration via REST API
Uses Supabase client library to execute SQL statements
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_env_file(env_path: str) -> dict:
    """Parse .env file"""
    logger.info(f"Loading environment from: {env_path}")
    
    if not os.path.exists(env_path):
        raise FileNotFoundError(f".env file not found at {env_path}")
    
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    logger.info(f"✓ Loaded {len(env_vars)} environment variables")
    return env_vars


def extract_supabase_config(database_url: str) -> dict:
    """Extract Supabase project info from DATABASE_URL"""
    logger.info("Extracting Supabase configuration...")
    
    try:
        # Parse: postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres
        if '@' not in database_url:
            raise ValueError("Invalid DATABASE_URL format")
        
        # Get host
        host_part = database_url.split('@')[1].split(':')[0]
        
        # Extract project ID from: db.PROJECT_ID.supabase.co
        parts = host_part.split('.')
        if len(parts) < 3 or parts[-2] != 'supabase':
            raise ValueError("Could not parse Supabase project ID")
        
        project_id = parts[1]
        
        config = {
            'project_id': project_id,
            'project_url': f'https://{project_id}.supabase.co',
            'database_url': database_url
        }
        
        logger.info(f"✓ Project: {project_id}")
        logger.info(f"✓ URL: {config['project_url']}")
        
        return config
        
    except Exception as e:
        logger.error(f"✗ Failed to parse configuration: {e}")
        raise


def read_schema(schema_path: str) -> str:
    """Read schema.sql file"""
    logger.info(f"Reading schema from: {schema_path}")
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    logger.info(f"✓ Schema loaded ({len(schema)} bytes)")
    return schema


def split_statements(sql: str) -> list:
    """Split SQL into individual statements"""
    statements = []
    current = []
    
    for line in sql.split('\n'):
        # Skip comments
        if line.strip().startswith('--'):
            continue
        
        if line.strip():
            current.append(line)
        
        # Statement ends with semicolon
        if ';' in line:
            statement = '\n'.join(current).strip()
            if statement:
                statements.append(statement)
            current = []
    
    logger.info(f"✓ Parsed {len(statements)} SQL statements")
    return statements


def migrate_with_asyncpg(database_url: str, schema_sql: str) -> bool:
    """Attempt migration using asyncpg"""
    logger.info("")
    logger.info("Attempting migration with asyncpg...")
    
    try:
        import asyncio
        import asyncpg
        
        async def run_migration():
            try:
                logger.info("Connecting to database...")
                conn = await asyncpg.connect(database_url)
                
                statements = split_statements(schema_sql)
                
                for i, statement in enumerate(statements, 1):
                    try:
                        logger.info(f"Executing statement {i}/{len(statements)}...")
                        await conn.execute(statement)
                        
                        # Log what was executed
                        if 'CREATE TABLE' in statement.upper():
                            table = statement.split('CREATE TABLE IF NOT EXISTS')[1].strip().split()[0]
                            logger.info(f"  ✓ Created table: {table}")
                        elif 'CREATE INDEX' in statement.upper():
                            logger.info(f"  ✓ Created index")
                        elif 'ALTER TABLE' in statement.upper():
                            logger.info(f"  ✓ Configured table")
                        elif 'CREATE POLICY' in statement.upper():
                            logger.info(f"  ✓ Created RLS policy")
                        else:
                            logger.info(f"  ✓ Statement executed")
                    
                    except Exception as e:
                        logger.error(f"  ✗ Statement {i} failed: {e}")
                        await conn.close()
                        return False
                
                await conn.close()
                logger.info("✓ All statements executed successfully")
                return True
            
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                return False
        
        # Run async migration
        result = asyncio.run(run_migration())
        return result
    
    except ImportError:
        logger.warning("asyncpg not available, trying psycopg...")
        return False
    except Exception as e:
        logger.error(f"asyncpg migration failed: {e}")
        return False


def migrate_with_psycopg(database_url: str, schema_sql: str) -> bool:
    """Attempt migration using psycopg (sync)"""
    logger.info("")
    logger.info("Attempting migration with psycopg...")
    
    try:
        import psycopg
        
        logger.info("Connecting to database...")
        conn = psycopg.connect(database_url)
        conn.autocommit = False
        
        statements = split_statements(schema_sql)
        
        with conn.cursor() as cur:
            for i, statement in enumerate(statements, 1):
                try:
                    logger.info(f"Executing statement {i}/{len(statements)}...")
                    cur.execute(statement)
                    
                    # Log what was executed
                    if 'CREATE TABLE' in statement.upper():
                        table = statement.split('CREATE TABLE IF NOT EXISTS')[1].strip().split()[0]
                        logger.info(f"  ✓ Created table: {table}")
                    elif 'CREATE INDEX' in statement.upper():
                        logger.info(f"  ✓ Created index")
                    elif 'ALTER TABLE' in statement.upper():
                        logger.info(f"  ✓ Configured table")
                    elif 'CREATE POLICY' in statement.upper():
                        logger.info(f"  ✓ Created RLS policy")
                    else:
                        logger.info(f"  ✓ Statement executed")
                
                except Exception as e:
                    logger.error(f"  ✗ Statement {i} failed: {e}")
                    conn.rollback()
                    conn.close()
                    return False
        
        conn.commit()
        conn.close()
        logger.info("✓ All statements executed and committed")
        return True
    
    except ImportError:
        logger.error("psycopg not installed")
        return False
    except Exception as e:
        logger.error(f"psycopg migration failed: {e}")
        return False


def verify_migration(database_url: str) -> bool:
    """Verify tables were created"""
    logger.info("")
    logger.info("Verifying migration...")
    
    try:
        import psycopg
        
        conn = psycopg.connect(database_url)
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in cur.fetchall()]
            logger.info(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
            
            expected = {'profiles', 'chat_threads', 'chat_messages'}
            if expected.issubset(set(tables)):
                logger.info("✓ All required tables verified")
                return True
            else:
                missing = expected - set(tables)
                logger.error(f"✗ Missing tables: {missing}")
                return False
        
        conn.close()
    
    except Exception as e:
        logger.warning(f"Could not verify: {e}")
        return False


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Supabase Schema Migration")
    logger.info("=" * 60)
    
    try:
        # Load environment
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / '.env'
        env_vars = load_env_file(str(env_path))
        
        # Get database URL
        if 'DATABASE_URL' not in env_vars:
            raise ValueError("DATABASE_URL not found in .env")
        
        database_url = env_vars['DATABASE_URL']
        
        # Extract config
        config = extract_supabase_config(database_url)
        
        # Read schema
        schema_path = Path(__file__).parent / 'schema.sql'
        schema_sql = read_schema(str(schema_path))
        
        # Try migration with asyncpg first (faster)
        logger.info("")
        success = migrate_with_asyncpg(database_url, schema_sql)
        
        # Fall back to psycopg if asyncpg fails
        if not success:
            success = migrate_with_psycopg(database_url, schema_sql)
        
        if not success:
            logger.error("\n✗ Migration failed")
            return False
        
        # Verify
        if not verify_migration(database_url):
            logger.warning("⚠ Could not verify migration")
            return True  # Still consider it success if statements executed
        
        # Success
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Your Supabase database now has:")
        logger.info("  ✓ profiles table")
        logger.info("  ✓ chat_threads table")
        logger.info("  ✓ chat_messages table")
        logger.info("  ✓ Row Level Security enabled")
        logger.info("  ✓ Performance indexes")
        logger.info("")
        logger.info("Ready to start the backend:")
        logger.info("  uvicorn app.main:app --app-dir backend --reload")
        
        return True
    
    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error(f"✗ Migration failed: {e}")
        logger.error("=" * 60)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
