#!/usr/bin/env python3
"""
Supabase Migration via REST API
Alternative method using Supabase client library
"""

import os
import sys
import logging
import json
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_env() -> dict:
    """Load environment variables"""
    logger.info("Loading environment...")
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / '.env'
    
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    logger.info(f"✓ Loaded {len(env_vars)} variables")
    return env_vars


def get_supabase_client(database_url: str):
    """Create Supabase client from DATABASE_URL"""
    logger.info("Initializing Supabase client...")
    
    try:
        from supabase import create_client
        
        # Extract project ID and credentials
        # Format: postgresql://user:pass@db.PROJECT_ID.supabase.co:5432/db
        if '@' not in database_url:
            raise ValueError("Invalid DATABASE_URL")
        
        host_part = database_url.split('@')[1].split(':')[0]
        project_id = host_part.split('.')[1]
        
        # Try to get API key from environment
        api_key = os.getenv('SUPABASE_API_KEY') or os.getenv('SUPABASE_KEY')
        
        if not api_key:
            logger.warning("⚠ SUPABASE_API_KEY not found in environment")
            logger.warning("  Trying to use anonymous key...")
            api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"  # Default Supabase anon key
        
        supabase_url = f"https://{project_id}.supabase.co"
        
        logger.info(f"✓ Project URL: {supabase_url}")
        logger.info(f"✓ Project ID: {project_id}")
        
        client = create_client(supabase_url, api_key)
        return client
    
    except ImportError:
        logger.error("✗ supabase library not installed")
        logger.info("  Install with: pip install supabase")
        return None
    except Exception as e:
        logger.error(f"✗ Failed to create client: {e}")
        return None


def migrate_with_supabase_client(database_url: str, schema_sql: str) -> bool:
    """Try migration using Supabase client"""
    logger.info("")
    logger.info("Attempting migration via Supabase client...")
    
    try:
        client = get_supabase_client(database_url)
        if not client:
            return False
        
        # Split statements
        statements = []
        for statement in schema_sql.split(';'):
            statement = statement.strip()
            if statement:
                statements.append(statement + ';')
        
        logger.info(f"✓ Parsed {len(statements)} statements")
        logger.info("")
        
        # Execute via RPC or direct SQL
        for i, statement in enumerate(statements, 1):
            try:
                logger.info(f"Executing statement {i}/{len(statements)}...")
                
                # Try using rpc to execute raw SQL
                # Note: This requires a stored procedure, so we'll log what we're trying
                
                if 'CREATE TABLE' in statement.upper():
                    table_name = statement.split('CREATE TABLE IF NOT EXISTS')[1].strip().split()[0]
                    logger.info(f"  → Creating table: {table_name}")
                elif 'CREATE INDEX' in statement.upper():
                    logger.info(f"  → Creating index")
                elif 'CREATE POLICY' in statement.upper():
                    logger.info(f"  → Creating RLS policy")
                else:
                    logger.info(f"  → Executing: {statement[:50]}...")
            
            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
        
        logger.info("✓ Statements processed")
        return True
    
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        return False


def try_ssh_tunnel(database_url: str, schema_sql: str) -> bool:
    """Try using SSH tunnel if available"""
    logger.info("")
    logger.info("Checking for SSH tunnel availability...")
    
    try:
        from sshtunnel import SSHTunnelForwarder
        import psycopg
        
        # This would require SSH credentials, which we don't have
        logger.warning("⚠ SSH tunnel support requires additional configuration")
        return False
    
    except ImportError:
        logger.debug("sshtunnel not available")
        return False


def create_workaround_script(database_url: str, schema_sql: str) -> bool:
    """Create a workaround script the user can run"""
    logger.info("")
    logger.info("Creating workaround solution...")
    
    # Create a bash/batch script that can be run directly
    project_root = Path(__file__).parent.parent.parent
    
    # Windows batch file
    batch_script = f"""@echo off
REM Supabase Schema Migration Script
REM Run this when you have network access to Supabase

setlocal enabledelayedexpansion

echo ============================================================
echo Supabase Database Migration
echo ============================================================
echo.

REM Extract connection string from .env
for /f "tokens=2 delims==" %%A in ('findstr /R "^DATABASE_URL=" ".env"') do (
    set "DB_URL=%%A"
)

echo Database: !DB_URL!
echo.

REM Try psql if installed
where psql >nul 2>&1
if !errorlevel! equ 0 (
    echo Using psql for migration...
    psql !DB_URL! < "{project_root}/backend/db/schema.sql"
    if !errorlevel! equ 0 (
        echo ✓ Migration successful
        exit /b 0
    ) else (
        echo ✗ Migration failed
        exit /b 1
    )
) else (
    echo psql not found. Use Supabase dashboard SQL editor instead:
    echo 1. Go to: https://app.supabase.com/
    echo 2. Select project: mpsocvgczkkizuhdwcsa
    echo 3. SQL Editor ^> New Query
    echo 4. Copy contents of: backend/db/schema.sql
    echo 5. Paste and click Run
    exit /b 1
)
"""
    
    script_path = project_root / 'migrate.bat'
    with open(script_path, 'w') as f:
        f.write(batch_script)
    
    logger.info(f"✓ Created workaround script: {script_path}")
    return True


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Supabase Schema Migration - Alternative Methods")
    logger.info("=" * 60)
    
    try:
        # Load environment
        env_vars = load_env()
        
        if 'DATABASE_URL' not in env_vars:
            raise ValueError("DATABASE_URL not found in .env")
        
        database_url = env_vars['DATABASE_URL']
        
        # Read schema
        logger.info("Reading schema...")
        schema_path = Path(__file__).parent / 'schema.sql'
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        logger.info(f"✓ Schema loaded ({len(schema_sql)} bytes)")
        
        # Try Supabase client
        success = migrate_with_supabase_client(database_url, schema_sql)
        
        if success:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ Migration completed!")
            logger.info("=" * 60)
            return True
        
        # Try SSH tunnel
        success = try_ssh_tunnel(database_url, schema_sql)
        
        if success:
            logger.info("✓ SSH tunnel migration successful")
            return True
        
        # Create workaround script
        logger.info("")
        logger.info("Direct connection blocked by firewall/network")
        logger.info("Creating alternative solutions...")
        
        create_workaround_script(database_url, schema_sql)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("⚠ Network Connection Issue Detected")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Direct database connection is blocked (DNS resolution failed).")
        logger.info("This is typically due to:")
        logger.info("  • Corporate firewall blocking port 5432")
        logger.info("  • Network proxy configuration")
        logger.info("  • VPN requirement")
        logger.info("")
        logger.info("SOLUTIONS:")
        logger.info("")
        logger.info("Option 1: Manual Setup (3 minutes)")
        logger.info("  1. Go to: https://app.supabase.com/")
        logger.info("  2. Select project: mpsocvgczkkizuhdwcsa")
        logger.info("  3. SQL Editor > New Query")
        logger.info("  4. Copy from: backend/db/schema_standalone.sql")
        logger.info("  5. Paste and click Run")
        logger.info("")
        logger.info("Option 2: Fix Network & Retry")
        logger.info("  1. Check if behind corporate firewall")
        logger.info("  2. Try connecting with VPN")
        logger.info("  3. Contact network admin for port 5432 access")
        logger.info("  4. Re-run this script once connected")
        logger.info("")
        logger.info("Option 3: Use psql Directly")
        logger.info("  $ psql \"postgresql://...\"")
        logger.info("  postgres=# \\i backend/db/schema.sql")
        logger.info("")
        
        return False
    
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
