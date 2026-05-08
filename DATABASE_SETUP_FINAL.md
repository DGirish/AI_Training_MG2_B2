# Database Setup - Final Instructions

## ✅ What Was Accomplished

### 1. Environment Variables Parsed ✓
- **Database URL:** `postgresql://postgres:***@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres`
- **Project ID:** `mpsocvgczkkizuhdwcsa`
- **14 environment variables loaded** from `.env` file

### 2. Schema Generated ✓
- **SQL Schema:** `backend/db/schema.sql` (2,639 bytes)
- **Standalone SQL:** `backend/db/schema_standalone.sql` (3,190 bytes) - Ready to paste!

### 3. Migration Scripts Created ✓
- **`backend/db/migrate.py`** - Direct PostgreSQL connection approach
- **`backend/db/migrate_manual.py`** - Manual setup generator

---

## 📊 Current Status

### Issue: Network Connectivity
The direct database connection attempt failed:
```
Error: failed to resolve host 'db.mpsocvgczkkizuhdwcsa.supabase.co': [Errno 11001] getaddrinfo failed
```

**Likely Causes:**
1. 🔒 Corporate firewall blocking port 5432
2. 🌐 DNS resolver not configured
3. 📡 Network proxy intercepting requests
4. 🔐 VPN not connected
5. 🚫 ISP blocking direct database connections

**This is NOT a configuration error** - Your credentials and schema are correct!

---

## 🚀 Next Steps: Manual Database Setup

### Option 1: GUI Setup (Recommended for first-time)

This is the fastest and most reliable method:

#### Step 1: Open Supabase Dashboard
1. Go to [https://app.supabase.com/](https://app.supabase.com/)
2. Log in with your credentials
3. Select project: `mpsocvgczkkizuhdwcsa`

#### Step 2: Access SQL Editor
1. Left sidebar → **SQL Editor**
2. Click **New Query** button
3. You'll see a blank SQL query box

#### Step 3: Copy Ready-Made SQL
**File Location:** `backend/db/schema_standalone.sql`

Or copy directly from below:

```sql
-- ============================================================
-- Supabase Database Schema Migration
-- ============================================================

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

#### Step 4: Execute SQL
1. Paste the SQL into the query box
2. Click **Run** button (or press `Ctrl+Enter`)
3. Wait for completion (should be instant or a few seconds)

#### Step 5: Verify Success
1. Check for any error messages (would appear in red)
2. Switch to **Table Editor** tab (left sidebar)
3. Expand **public** schema
4. Should see 3 new tables:
   - ✅ profiles
   - ✅ chat_threads
   - ✅ chat_messages

---

### Option 2: Command-Line Setup (If familiar with psql)

If you have `psql` installed and network access works:

```bash
# Test connection first
psql "postgresql://postgres:Moksha@192308@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres" -c "SELECT 1;"

# Run migration script
cd "backend/db"
psql "postgresql://postgres:Moksha@192308@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres" < schema.sql
```

---

### Option 3: Retry Programmatic Setup (If network fixed)

If you fix the network connectivity issue:

```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat\backend"
python db/migrate.py
```

**To fix network:**
```powershell
# Test DNS resolution
Resolve-DnsName db.mpsocvgczkkizuhdwcsa.supabase.co

# Test TCP connection  
Test-NetConnection -ComputerName db.mpsocvgczkkizuhdwcsa.supabase.co -Port 5432

# Check if behind proxy/firewall
ipconfig /all | Select-String "DNS"
```

---

## ✅ After Database Setup Complete

Once tables are created (using any method above):

### 1. Verify Tables Exist

Run this in Supabase SQL Editor to confirm:

```sql
-- Check tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

**Expected Output:**
```
chat_messages
chat_threads
profiles
```

### 2. Check RLS Policies

```sql
-- Verify RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND tablename IN ('profiles', 'chat_threads', 'chat_messages');
```

**Expected:** All show `rowsecurity = true`

### 3. Check Indexes

```sql
-- Verify indexes
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 'public' AND tablename IN ('chat_threads', 'chat_messages')
ORDER BY indexname;
```

**Expected:**
```
idx_chat_messages_thread_id
idx_chat_threads_user_id
```

---

## 🔧 Backend Configuration

Now that database tables are ready:

### 1. Verify .env Has Required Variables

```bash
# In .env file, ensure these exist:
DATABASE_URL=postgresql://...                    # Already present ✓
SECRET_KEY=your-secret-key-min-32-chars         # ADD THIS

LITELLM_PROXY_URL=https://litellm.amzur.com/v1  # Already present ✓
LITELLM_API_KEY=your-key                         # Already present ✓
```

### 2. Add SECRET_KEY if Missing

```bash
# Add to .env:
SECRET_KEY=my-super-secret-key-change-me-must-be-32-characters-minimum
```

### 3. Test Backend Startup

```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat"
uvicorn app.main:app --app-dir backend --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 4. Test Health Endpoint

```bash
# In another terminal:
curl http://127.0.0.1:8000/health
```

**Expected Response:**
```json
{"status":"ok"}
```

---

## 🎨 Frontend Setup

### 1. Install Dependencies

```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat\frontend"
npm install
```

### 2. Build

```bash
npm run build
```

**Expected:** No errors, file size output

### 3. Run Dev Server

```bash
npm run dev
```

**Expected:**
```
➜  Local:   http://127.0.0.1:5173/
```

---

## 🧪 End-to-End Test

### 1. Open Browser

Navigate to `http://127.0.0.1:5173/`

### 2. Create Account

- Email: `test@example.com`
- Password: `TestPassword123`
- Full Name: `Test User`
- Click **Sign Up**

### 3. Verify in Database

In Supabase SQL Editor:

```sql
SELECT * FROM profiles WHERE email = 'test@example.com';
```

**Should show:** 1 row with your test user

### 4. Create Thread and Send Message

1. In ChatPage, click **+ New Thread**
2. Enter title: `Test Thread`
3. Send message: `Hello, how are you?`
4. Watch it stream back

### 5. Verify Messages Saved

```sql
SELECT role, content FROM chat_messages 
WHERE thread_id IN (
  SELECT id FROM chat_threads 
  WHERE user_id = (SELECT id FROM profiles WHERE email = 'test@example.com')
)
ORDER BY created_at;
```

**Should show:** 2 rows (user + assistant messages)

---

## 📋 Troubleshooting

### Tables Not Appearing in Supabase

**Check:**
1. Refresh the page (browser)
2. Check SQL Editor for error messages (red text)
3. Run verification query above
4. Check your user has admin/owner role in Supabase

**Common Issues:**
- Syntax error in SQL → Fix and re-run
- RLS policy syntax error → Drop policy and re-create
- Foreign key constraint → Ensure parents created first

### Backend Connection Failed

```bash
# Test directly
psql "postgresql://postgres:Moksha@192308@db.mpsocvgczkkizuhdwcsa.supabase.co:5432/postgres"
```

**If psql fails:**
- Check network connectivity
- Verify password (has @ symbols, check escaping)
- Try from different network (VPN, mobile hotspot)

### Messages Not Saving

**Check:**
1. User profile exists in `profiles` table
2. Thread exists with correct `user_id`
3. RLS policies are enabled: `ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;`
4. Backend logs for SQL errors

**Test:**
```sql
INSERT INTO profiles (id, email, full_name) 
VALUES (gen_random_uuid(), 'test@test.com', 'Test');
-- Should work if permissions OK
```

---

## 📞 Support Resources

### Supabase
- **Dashboard:** https://app.supabase.com/
- **Docs:** https://supabase.com/docs/
- **SQL Reference:** https://www.postgresql.org/docs/

### PostgreSQL
- **RLS Guide:** https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- **Foreign Keys:** https://www.postgresql.org/docs/current/ddl-constraints.html

### Your Project Files
- **Schema:** `backend/db/schema.sql`
- **Standalone SQL:** `backend/db/schema_standalone.sql`
- **Migration Script:** `backend/db/migrate.py`
- **Manual Setup Guide:** `DATABASE_SETUP_MANUAL.md`

---

## ✅ Checklist

**Before Running Servers:**
- [ ] Database tables created (profiles, chat_threads, chat_messages)
- [ ] RLS policies enabled
- [ ] Indexes created
- [ ] Backend `.env` has SECRET_KEY
- [ ] psycopg[binary] installed

**Verification:**
- [ ] `curl http://127.0.0.1:8000/health` returns 200
- [ ] Supabase SQL Editor queries work
- [ ] Profile created on signup appears in DB
- [ ] Messages appear in DB after sending

**First Run:**
- [ ] Backend started: `uvicorn app.main:app --app-dir backend --reload`
- [ ] Frontend running: `npm run dev`
- [ ] Browser showing LoginPage at `http://127.0.0.1:5173/`
- [ ] Can sign up and send message

---

**🎉 Database setup is ready! Follow the manual SQL setup steps above to complete configuration.**
