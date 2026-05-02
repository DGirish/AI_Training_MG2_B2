#!/usr/bin/env python3
"""
Supabase Database Migration Script

This script:
1. Reads .env file for DATABASE_URL
2. Connects to Supabase PostgreSQL
3. Executes schema.sql to create tables
4. Provides detailed logging for each step
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_env_file(env_path: str) -> dict:
    """
    Parse .env file and return dictionary of environment variables.
    
    Args:
        env_path: Path to .env file
        
    Returns:
        Dictionary of environment variables
        
    Raises:
        FileNotFoundError: If .env file not found
    """
    logger.info(f"Loading environment from: {env_path}")
    
    if not os.path.exists(env_path):
        raise FileNotFoundError(f".env file not found at {env_path}")
    
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    logger.info(f"✓ Loaded {len(env_vars)} environment variables")
    return env_vars


def parse_database_url(database_url: str) -> dict:
    """
    Parse PostgreSQL connection string.
    
    Args:
        database_url: PostgreSQL connection string (postgresql://user:pass@host:port/db)
        
    Returns:
        Dictionary with host, port, user, password, database
    """
    logger.info("Parsing DATABASE_URL...")
    
    try:
        # Remove postgresql:// or postgres:// prefix
        if database_url.startswith('postgresql://'):
            url = database_url.replace('postgresql://', '', 1)
        elif database_url.startswith('postgres://'):
            url = database_url.replace('postgres://', '', 1)
        else:
            raise ValueError("Invalid database URL format")
        
        # Parse components
        if '@' in url:
            credentials, host_db = url.rsplit('@', 1)
            user, password = credentials.split(':', 1) if ':' in credentials else (credentials, '')
        else:
            raise ValueError("Invalid database URL format (missing @)")
        
        if ':' in host_db:
            host_port, database = host_db.rsplit('/', 1)
            host, port = host_port.rsplit(':', 1)
        else:
            raise ValueError("Invalid database URL format (missing port)")
        
        config = {
            'host': host,
            'port': int(port),
            'user': user,
            'password': password,
            'database': database
        }
        
        logger.info(f"✓ Parsed connection: {user}@{host}:{port}/{database}")
        return config
        
    except Exception as e:
        logger.error(f"✗ Failed to parse DATABASE_URL: {e}")
        raise


def test_connection(db_config: dict) -> bool:
    """
    Test PostgreSQL connection without executing migrations.
    
    Args:
        db_config: Database configuration dictionary
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        import psycopg
        logger.info("Attempting database connection...")
        
        conn = psycopg.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        
        # Test query
        with conn.cursor() as cur:
            cur.execute('SELECT VERSION();')
            version = cur.fetchone()
            logger.info(f"✓ Connected successfully")
            logger.info(f"  Database: {version[0][:100]}")
        
        conn.close()
        return True
        
    except ImportError:
        logger.error("✗ psycopg module not found")
        logger.info("  Install with: pip install psycopg[binary]")
        return False
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return False


def read_schema_file(schema_path: str) -> str:
    """
    Read and validate schema.sql file.
    
    Args:
        schema_path: Path to schema.sql file
        
    Returns:
        Schema SQL as string
        
    Raises:
        FileNotFoundError: If schema.sql not found
    """
    logger.info(f"Reading schema from: {schema_path}")
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    logger.info(f"✓ Schema file loaded ({len(schema_sql)} bytes)")
    return schema_sql


def split_sql_statements(sql: str) -> list:
    """
    Split SQL file into individual statements.
    Respects multi-line statements and comments.
    
    Args:
        sql: SQL text
        
    Returns:
        List of SQL statements
    """
    statements = []
    current = []
    in_comment = False
    
    for line in sql.split('\n'):
        # Handle comments
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
    
    # Add any remaining statement
    statement = '\n'.join(current).strip()
    if statement:
        statements.append(statement)
    
    logger.info(f"✓ Parsed {len(statements)} SQL statements")
    return statements


def execute_migration(db_config: dict, schema_sql: str) -> bool:
    """
    Execute SQL statements to create tables.
    
    Args:
        db_config: Database configuration dictionary
        schema_sql: SQL statements to execute
        
    Returns:
        True if all statements executed successfully
    """
    try:
        import psycopg
    except ImportError:
        logger.error("✗ psycopg module not found")
        logger.info("  Install with: pip install psycopg[binary]")
        return False
    
    statements = split_sql_statements(schema_sql)
    
    try:
        logger.info("Connecting to database...")
        conn = psycopg.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        
        # Disable autocommit to allow transaction control
        conn.autocommit = False
        
        with conn.cursor() as cur:
            for i, statement in enumerate(statements, 1):
                try:
                    logger.info(f"Executing statement {i}/{len(statements)}...")
                    
                    # Log first 60 chars of statement
                    stmt_preview = statement[:60].replace('\n', ' ')
                    if len(statement) > 60:
                        stmt_preview += "..."
                    logger.debug(f"  SQL: {stmt_preview}")
                    
                    cur.execute(statement)
                    
                    # Determine what was executed
                    if 'CREATE TABLE' in statement.upper():
                        table_match = statement.upper().split('CREATE TABLE IF NOT EXISTS')[1].strip().split()[0]
                        logger.info(f"  ✓ Table: {table_match}")
                    elif 'CREATE INDEX' in statement.upper():
                        idx_match = statement.upper().split('CREATE INDEX IF NOT EXISTS')[1].strip().split()[0]
                        logger.info(f"  ✓ Index: {idx_match}")
                    elif 'ALTER TABLE' in statement.upper():
                        logger.info(f"  ✓ Altered table configuration")
                    elif 'CREATE POLICY' in statement.upper():
                        logger.info(f"  ✓ Created RLS policy")
                    else:
                        logger.info(f"  ✓ Statement executed")
                    
                except Exception as e:
                    logger.error(f"  ✗ Statement {i} failed: {e}")
                    logger.error(f"  Statement: {statement[:100]}...")
                    conn.rollback()
                    return False
        
        # Commit all changes
        conn.commit()
        logger.info("✓ All changes committed")
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Database operation failed: {e}")
        return False


def verify_tables(db_config: dict) -> bool:
    """
    Verify that all expected tables exist in the database.
    
    Args:
        db_config: Database configuration dictionary
        
    Returns:
        True if all tables exist
    """
    try:
        import psycopg
    except ImportError:
        logger.warning("⚠ Cannot verify tables without psycopg")
        return False
    
    expected_tables = ['profiles', 'chat_threads', 'chat_messages']
    
    try:
        logger.info("Verifying table creation...")
        conn = psycopg.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        
        with conn.cursor() as cur:
            # Query information schema for tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """)
            
            existing_tables = {row[0] for row in cur.fetchall()}
            logger.debug(f"  Found tables: {existing_tables}")
            
            all_exist = True
            for table in expected_tables:
                if table in existing_tables:
                    logger.info(f"  ✓ {table}")
                else:
                    logger.error(f"  ✗ {table} not found")
                    all_exist = False
            
            if all_exist:
                logger.info("✓ All tables verified successfully")
            else:
                logger.error("✗ Some tables are missing")
            
            conn.close()
            return all_exist
        
    except Exception as e:
        logger.error(f"✗ Verification failed: {e}")
        return False


def main():
    """Main execution flow."""
    logger.info("=" * 60)
    logger.info("Supabase Database Migration Script")
    logger.info("=" * 60)
    
    try:
        # Step 1: Load environment
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / '.env'
        env_vars = load_env_file(str(env_path))
        
        # Step 2: Get DATABASE_URL
        if 'DATABASE_URL' not in env_vars:
            raise ValueError("DATABASE_URL not found in .env file")
        
        database_url = env_vars['DATABASE_URL']
        logger.info(f"✓ Found DATABASE_URL")
        
        # Step 3: Parse connection config
        db_config = parse_database_url(database_url)
        
        # Step 4: Test connection
        logger.info("")
        logger.info("Testing connection...")
        if not test_connection(db_config):
            logger.error("\n✗ Cannot proceed without database connection")
            return False
        
        # Step 5: Read schema file
        logger.info("")
        schema_path = Path(__file__).parent / 'schema.sql'
        schema_sql = read_schema_file(str(schema_path))
        
        # Step 6: Execute migration
        logger.info("")
        logger.info("Executing migration...")
        if not execute_migration(db_config, schema_sql):
            logger.error("\n✗ Migration failed")
            return False
        
        # Step 7: Verify tables
        logger.info("")
        if not verify_tables(db_config):
            logger.warning("\n⚠ Could not verify all tables")
            return False
        
        # Success
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("\nYour Supabase database is ready:")
        logger.info("  - profiles table (user data)")
        logger.info("  - chat_threads table (conversations)")
        logger.info("  - chat_messages table (messages)")
        logger.info("  - Row Level Security (RLS) policies enabled")
        logger.info("  - Indexes created for performance")
        logger.info("")
        logger.info("You can now start the backend server:")
        logger.info("  uvicorn app.main:app --app-dir backend --reload")
        
        return True
        
    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error(f"✗ Migration failed with error:")
        logger.error(f"  {e}")
        logger.error("=" * 60)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
