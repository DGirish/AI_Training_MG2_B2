# Supabase Database Migration Guide

## Issue: DNS Resolution Failed

The migration script encountered a DNS resolution error connecting to your Supabase host:
- **Host:** `db.mpsocvgczkkizuhdwcsa.supabase.co`
- **Error:** `failed to resolve host ... [Errno 11001] getaddrinfo failed`

This typically indicates:
1. **Network connectivity issue** (firewall, proxy, or VPN blocking access)
2. **DNS server not configured** 
3. **Supabase domain is unreachable** from your network

## Solution: Manual Migration via Supabase Dashboard

Follow these steps to create your database schema using the Supabase web interface:

### Step 1: Access Supabase SQL Editor

1. Open [Supabase Dashboard](https://app.supabase.com/)
2. Select your project: `mpsocvgczkkizuhdwcsa`
3. Navigate to **SQL Editor** (left sidebar)
4. Click **New Query**

### Step 2: Copy SQL Statements

The SQL schema is located at:
```
backend/db/schema.sql
```

Or copy the complete schema below:

```sql
-- Profiles table (synced with Supabase auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat threads table
CREATE TABLE IF NOT EXISTS chat_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES chat_threads (id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_chat_threads_user_id ON chat_threads (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_id ON chat_messages (thread_id, created_at ASC);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- RLS policies for profiles
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- RLS policies for chat_threads
CREATE POLICY "Users can view own threads" ON chat_threads
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create threads" ON chat_threads
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own threads" ON chat_threads
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own threads" ON chat_threads
    FOR DELETE USING (auth.uid() = user_id);

-- RLS policies for chat_messages
CREATE POLICY "Users can view messages in own threads" ON chat_messages
    FOR SELECT USING (
        auth.uid() IN (
            SELECT user_id FROM chat_threads WHERE id = chat_messages.thread_id
        )
    );

CREATE POLICY "Users can insert messages in own threads" ON chat_messages
    FOR INSERT WITH CHECK (
        auth.uid() = user_id AND
        auth.uid() IN (
            SELECT user_id FROM chat_threads WHERE id = thread_id
        )
    );
```

### Step 3: Execute SQL in Supabase

1. Copy the entire SQL above
2. Paste into the SQL Editor query box
3. Click **Run** button (or press `Cmd+Enter` / `Ctrl+Enter`)
4. Wait for execution to complete
5. Check for success messages

### Step 4: Verify Tables

After successful execution, verify tables were created:

```sql
-- List all tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
```

Expected output:
```
profiles
chat_threads
chat_messages
```

### Step 5: Verify RLS Policies

```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname = 'public' AND tablename IN ('profiles', 'chat_threads', 'chat_messages');
```

Expected: All tables should have `rowsecurity = t` (true)

---

## Alternative: Fix Network Connectivity

If you want to use the automated migration script, resolve the DNS issue:

### Option 1: Check Network Connectivity

```powershell
# Test DNS resolution
Resolve-DnsName db.mpsocvgczkkizuhdwcsa.supabase.co

# Test TCP connection
Test-NetConnection -ComputerName db.mpsocvgczkkizuhdwcsa.supabase.co -Port 5432
```

### Option 2: Check Firewall

- Verify port 5432 is not blocked
- Check if you're behind a corporate proxy
- Try connecting with a VPN if needed

### Option 3: Try Direct Connection

Test connection directly:

```bash
# Using psql (if installed)
psql "postgresql://postgres:Moksha@192308@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres"

# Or using Python
python -c "
import psycopg
conn = psycopg.connect('postgresql://postgres:Moksha@192308@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres')
print('Connected successfully!')
conn.close()
"
```

If successful, run the migration script again:

```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat\backend"
python db/migrate.py
```

---

## Expected Output After Migration

Once tables are successfully created, you should see:

✅ **3 Tables Created:**
- `profiles` - User account data
- `chat_threads` - Conversation threads
- `chat_messages` - Individual messages

✅ **2 Indexes Created:**
- `idx_chat_threads_user_id` - Fast thread lookup by user
- `idx_chat_messages_thread_id` - Fast message lookup by thread

✅ **RLS Enabled:** All tables protected with Row-Level Security policies

✅ **Policies Created:** 6 policies ensuring users can only access their own data

---

## Verification Queries

Run these in Supabase SQL editor to verify setup:

### Check Tables Exist
```sql
SELECT COUNT(*) as table_count FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- Should return: 3
```

### Check Indexes
```sql
SELECT indexname FROM pg_indexes 
WHERE schemaname = 'public' AND tablename IN ('chat_threads', 'chat_messages');
-- Should return: idx_chat_threads_user_id, idx_chat_messages_thread_id
```

### Check RLS Policies
```sql
SELECT policyname, tablename FROM pg_policies 
WHERE schemaname = 'public' ORDER BY tablename;
-- Should return: 6 policies across the 3 tables
```

### Check Relationships
```sql
-- View foreign key constraints
SELECT constraint_name, table_name, referenced_table_name 
FROM information_schema.key_column_usage 
WHERE table_schema = 'public' AND referenced_table_name IS NOT NULL;
```

---

## Environment Variables Confirmed

Your `.env` file has been read successfully:

```
✓ DATABASE_URL: postgresql://postgres:***@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres
✓ LITELLM_PROXY_URL: https://litellm.amzur.com/v1
✓ LLM_MODEL: (configured)
✓ And 11 other variables loaded
```

---

## Next Steps

### After Manual SQL Migration:

1. **Verify in Supabase:**
   - Check **Table Editor** in sidebar shows 3 new tables
   - View **Policies** tab for RLS policies

2. **Update Backend Config:**
   - Ensure `DATABASE_URL` is in `.env` (already present)
   - Ensure `SECRET_KEY` is set:
     ```bash
     # Add to .env if not present
     SECRET_KEY=your-secret-key-change-in-production-must-be-32-chars-min
     ```

3. **Start Backend Server:**
   ```bash
   cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat"
   uvicorn app.main:app --app-dir backend --reload
   ```

4. **Test Database Connection:**
   ```bash
   curl http://127.0.0.1:8000/health
   # Should return: {"status":"ok"}
   ```

5. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

---

## Troubleshooting

### Tables Not Appearing

1. Check for SQL errors in Supabase (error panel should show)
2. Try creating one table at a time
3. Verify you have permission to create tables

### RLS Policies Not Working

1. Ensure you've authenticated with Supabase Auth first
2. Check that `auth.uid()` is being called correctly
3. Verify user_id matches auth.uid() in test data

### Foreign Key Errors

1. Create `profiles` table first
2. Ensure UUIDs are properly formatted
3. Check profile exists before creating threads

### Connection Still Failing

1. Try the direct psql connection test
2. Contact your network administrator about firewall rules
3. Verify Supabase project is running (check Supabase dashboard)

---

## Support

- **Supabase Docs:** https://supabase.com/docs
- **SQL Reference:** https://www.postgresql.org/docs/current/
- **RLS Guide:** https://supabase.com/docs/guides/auth/row-level-security

For connection issues, check:
1. Supabase project status
2. Network connectivity (VPN, proxy, firewall)
3. Database credentials in `.env`
4. Host name resolution with `nslookup` or `Resolve-DnsName`
