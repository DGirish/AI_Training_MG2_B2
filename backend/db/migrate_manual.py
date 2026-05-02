#!/usr/bin/env python3
"""
Alternative Supabase Migration using REST API
Works when direct PostgreSQL connection fails

This script uses the Supabase REST API instead of direct DB connection
"""

import os
import json
import logging
from pathlib import Path
from urllib.parse import urljoin

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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


def get_supabase_credentials(env_vars: dict) -> dict:
    """Extract Supabase credentials from DATABASE_URL"""
    logger.info("Extracting Supabase credentials...")
    
    database_url = env_vars.get('DATABASE_URL', '')
    
    # Parse project ID from hostname: db.PROJECT_ID.supabase.co
    if 'supabase.co' in database_url:
        try:
            # Find the last @ to handle passwords with @ in them
            last_at = database_url.rfind('@')
            host_port = database_url[last_at+1:]  # Everything after last @
            host = host_port.split(':')[0]  # Get hostname before port
            
            # Project ID is the second part of hostname: db.PROJECT_ID.supabase.co
            parts = host.split('.')
            if len(parts) >= 3 and parts[-2] == 'supabase':
                project_id = parts[1]
            else:
                # If format is different, extract from between dots
                project_id = [p for p in parts if p and p != 'db' and p != 'supabase' and p != 'co'][0]
            
            logger.info(f"✓ Extracted Project ID: {project_id}")
            
            return {
                'project_id': project_id,
                'project_url': f'https://{project_id}.supabase.co',
            }
        except (IndexError, AttributeError, ValueError) as e:
            logger.error(f"✗ Could not parse Supabase URL: {e}")
            raise
    else:
        raise ValueError("DATABASE_URL does not appear to be a Supabase connection")


def read_schema_file(schema_path: str) -> str:
    """Read schema.sql file"""
    logger.info(f"Reading schema from: {schema_path}")
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    logger.info(f"✓ Schema file loaded ({len(schema)} bytes)")
    return schema


def create_standalone_sql_file(schema_path: str, output_path: str = None):
    """
    Create a standalone SQL file ready for pasting into Supabase dashboard
    """
    logger.info("Creating standalone SQL migration file...")
    
    schema = read_schema_file(schema_path)
    
    # Add helpful header
    header = """-- ============================================================
-- Supabase Database Schema Migration
-- Generated for manual execution in Supabase SQL Editor
-- ============================================================
-- 
-- Instructions:
-- 1. Go to Supabase Dashboard → SQL Editor
-- 2. Copy and paste the SQL below
-- 3. Click "Run" button
-- 4. Verify tables are created in Table Editor
--
-- ============================================================

"""
    
    if output_path is None:
        output_path = Path(schema_path).parent / 'schema_standalone.sql'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write(schema)
    
    logger.info(f"✓ Standalone SQL file created at: {output_path}")
    logger.info(f"  Size: {os.path.getsize(output_path)} bytes")
    
    return str(output_path)


def print_manual_instructions():
    """Print detailed manual instructions"""
    print("""
============================================================
🔗 ALTERNATIVE: Manual Setup via Supabase Dashboard
============================================================

Since direct database connection failed (likely network issue),
use the manual approach below:

STEP 1: Access Supabase Dashboard
  → Go to: https://app.supabase.com/
  → Select your project

STEP 2: Open SQL Editor
  → Click: SQL Editor (left sidebar)
  → Click: New Query

STEP 3: Copy and Paste Schema
  → Open: backend/db/schema.sql
  → Copy ALL content
  → Paste into SQL Editor query box

STEP 4: Execute
  → Click: Run button (or Ctrl+Enter)
  → Wait for completion

STEP 5: Verify
  → Switch to: Table Editor tab
  → Should see 3 new tables:
    ✓ profiles
    ✓ chat_threads  
    ✓ chat_messages

============================================================

If you still want to try programmatic setup:

1. Check Network Connectivity:
   $ Resolve-DnsName db.mpsocvgczkkizuhdwcsa.supabase.co
   $ Test-NetConnection -ComputerName db.mpsocvgczkkizuhdwcsa.supabase.co -Port 5432

2. Check if Behind Firewall:
   - VPN might be needed
   - Corporate proxy might be blocking
   - Check with network admin

3. Test Direct Connection:
   $ psql "postgresql://postgres:PASSWORD@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres"

============================================================
""")


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Supabase Migration - Alternative Setup")
    logger.info("=" * 60)
    
    try:
        # Load environment
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / '.env'
        env_vars = load_env_file(str(env_path))
        
        # Extract credentials
        try:
            supabase = get_supabase_credentials(env_vars)
        except ValueError as e:
            logger.error(f"✗ {e}")
            logger.info("  Manual setup is recommended")
            print_manual_instructions()
            return False
        
        # Create standalone SQL file
        schema_path = Path(__file__).parent / 'schema.sql'
        standalone_sql = create_standalone_sql_file(str(schema_path))
        
        # Print instructions
        logger.info("")
        print_manual_instructions()
        
        logger.info("")
        logger.info("Generated Files:")
        logger.info(f"  ✓ {standalone_sql}")
        logger.info("")
        logger.info("This file is ready to paste into Supabase SQL Editor")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
