# Complete Testing & Deployment Guide

## Phase 1: Environment Setup

### Step 1.1: Install Backend Dependencies

Open PowerShell and run:

```powershell
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat"
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Expected output: All packages installed successfully

### Step 1.2: Verify Requirements

```bash
pip list | grep -E "fastapi|sqlalchemy|langchain|supabase|passlib|python-jose"
```

Should show:
- fastapi >= 0.136
- sqlalchemy >= 2.0
- langchain-core >= 1.3
- supabase >= 2.4
- passlib >= 1.7
- python-jose >= 3.3
- asyncpg >= 3.0

### Step 1.3: Set Up .env

In project root `d:\. AI Forge Training\backend\Stackyon Intelligent Chat\`, create/update `.env`:

```bash
# Existing (from Phase 1)
LITELLM_PROXY_URL=https://litellm.amzur.com/v1
LITELLM_API_KEY=your-litellm-key-here
LLM_MODEL=gemini/gemini-2.5-flash
FRONTEND_ORIGIN=http://127.0.0.1:5173,http://localhost:5173

# New (for Supabase)
DATABASE_URL=postgresql://postgres:password@project.supabase.co:5432/postgres
SECRET_KEY=your-secret-key-min-32-chars-change-in-production-12345
```

**Where to get DATABASE_URL:**
1. Go to Supabase dashboard → Project Settings → Database
2. Copy "Connection string" (URI format)
3. Paste into DATABASE_URL

### Step 1.4: Frontend Dependencies

```bash
cd frontend
npm install
```

---

## Phase 2: Database Setup

### Step 2.1: Create Supabase Tables

1. Open Supabase dashboard → SQL editor
2. Copy entire contents of `backend/db/schema.sql`
3. Paste into SQL editor
4. Click "Run" button
5. Verify no errors

**Expected tables:**
- profiles
- chat_threads
- chat_messages

**Verify RLS is enabled:**
```sql
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname = 'public' AND tablename IN ('profiles', 'chat_threads', 'chat_messages');
```

All should show `t` (true) for rowsecurity.

### Step 2.2: Test Connection

```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat\backend"
python -c "
from app.db.session import engine
import asyncio

async def test():
    async with engine.begin() as conn:
        result = await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
        print('Database connection successful:', result.scalar())

asyncio.run(test())
"
```

Should print: `Database connection successful: 1`

---

## Phase 3: Backend Startup

### Step 3.1: Start Backend Server

```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat"
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Step 3.2: Verify Backend Health

Open another PowerShell window and test:

```bash
curl http://127.0.0.1:8000/health
```

Should return:
```json
{"status":"ok"}
```

---

## Phase 4: Frontend Startup

### Step 4.1: Build Frontend

```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat\frontend"
npm run build
```

Should complete with:
```
built in XXXms
```

### Step 4.2: Start Dev Server

```bash
npm run dev
```

Expected output:
```
➜  Local:   http://127.0.0.1:5173/
```

---

## Phase 5: End-to-End Testing

### Test 5.1: Sign Up Flow

1. Navigate to http://127.0.0.1:5173/
2. Should see LoginPage with "Sign Up" tab active
3. Enter:
   - Email: `test@example.com`
   - Password: `TestPassword123`
   - Full Name: `Test User`
4. Click "Sign Up"
5. Should redirect to ChatPage with your name displayed

**Verify in Supabase:**
```sql
SELECT * FROM profiles WHERE email = 'test@example.com';
```

### Test 5.2: Create Thread

1. Click "+ New Thread" in sidebar
2. Enter title: `Test Thread`
3. Click "Create"
4. New thread should appear in sidebar
5. Should switch to that thread

**Verify in Supabase:**
```sql
SELECT id, title, user_id FROM chat_threads ORDER BY created_at DESC LIMIT 1;
```

### Test 5.3: Send Message

1. In ChatPage, type message: `Hello, how are you?`
2. Click "Send"
3. Message should appear as user message
4. Assistant response should stream in
5. When complete, message should stop streaming

**Verify in Supabase:**
```sql
SELECT role, content FROM chat_messages ORDER BY created_at DESC LIMIT 2;
```

Should show:
- user: `Hello, how are you?`
- assistant: (full response)

### Test 5.4: Sign In Flow

1. Click "Logout" in ChatPage
2. Should redirect to LoginPage
3. Click "Sign In" tab
4. Enter email and password from Test 5.1
5. Click "Sign In"
6. Should redirect to ChatPage with previous threads loaded

### Test 5.5: Load Thread History

1. After sign in, sidebar should show "Test Thread"
2. Click on it
3. Previous messages should load
4. Should show your test message and assistant response

### Test 5.6: Multiple Threads

1. Create another thread: `Thread 2`
2. Send different message
3. Click back to "Test Thread"
4. Previous messages should be there
5. Click back to "Thread 2"
6. New messages should be there

---

## Phase 6: Performance & Security Testing

### Test 6.1: JWT Token Validation

1. Sign in
2. Open browser DevTools → Application → localStorage
3. Should see `token` key with long JWT string
4. Copy token value
5. Manually test endpoint:

```bash
curl "http://127.0.0.1:8000/api/auth/me?token=<paste-token>"
```

Should return your user profile.

### Test 6.2: Unauthorized Access

1. Try to access without token:

```bash
curl "http://127.0.0.1:8000/api/threads"
```

Should return 401 or error message.

### Test 6.3: RLS Policy Verification

1. Open Supabase SQL editor
2. Switch to different user role:

```sql
-- Create second test user
INSERT INTO profiles (id, email, full_name) 
VALUES ('12345678-1234-1234-1234-123456789012', 'other@example.com', 'Other User');

-- Try to query as if you're the other user
SET "app.jwt.claims.sub" = '12345678-1234-1234-1234-123456789012';
SELECT * FROM chat_threads;
SET "app.jwt.claims.sub" = DEFAULT;
```

Should return 0 rows (other user's threads are blocked).

### Test 6.4: Stream Latency

1. Open browser DevTools → Network tab
2. Send a message
3. Watch SSE stream
4. Should see tokens arriving roughly every 100-500ms
5. Total response time typically 3-10 seconds for full response

---

## Phase 7: Production Checklist

### Before Production Deployment

- [ ] Change `SECRET_KEY` in `.env` to a cryptographically random string (min 32 chars)
- [ ] Use strong PostgreSQL password in `DATABASE_URL`
- [ ] Set `FRONTEND_ORIGIN` to actual domain(s)
- [ ] Enable HTTPS on backend (use nginx/reverse proxy)
- [ ] Verify `LITELLM_API_KEY` is valid and has quota
- [ ] Test with real email domain (not localhost)
- [ ] Set up logging to CloudWatch / Datadog
- [ ] Configure database backups in Supabase
- [ ] Test RLS policies with multiple users
- [ ] Load test with at least 5 concurrent users

### Supabase Configuration

1. Go to Project Settings → Auth
2. Configure email domain (if using custom emails)
3. Set up email templates (optional)
4. Go to Database → Backups
5. Enable automatic backups (daily recommended)

### Environment Variables Checklist

```bash
# Required - Must change from defaults
SECRET_KEY=<32+ character random string>
DATABASE_URL=<production postgresql string>
LITELLM_API_KEY=<valid production key>

# Required - Keep from development
LITELLM_PROXY_URL=https://litellm.amzur.com/v1
LLM_MODEL=gemini/gemini-2.5-flash

# Required - Update for production domain
FRONTEND_ORIGIN=https://yourdomain.com,https://www.yourdomain.com
```

---

## Troubleshooting

### Error: "Module 'sqlalchemy' not found"
**Solution:** Run `pip install -r requirements.txt` in backend directory

### Error: "Database connection refused"
**Solution:** 
1. Check DATABASE_URL is correct
2. Verify Supabase project is running
3. Test connection with psql: `psql <DATABASE_URL>`

### Error: "CORS error" from frontend
**Solution:**
1. Backend logs should show which origin was blocked
2. Add origin to FRONTEND_ORIGIN in .env
3. Restart backend

### Error: "Token invalid" after login
**Solution:**
1. Check SECRET_KEY is same on backend
2. Verify token isn't expired (24 hour default)
3. Clear localStorage and sign in again

### Error: "Chat streaming stops mid-response"
**Solution:**
1. Check LiteLLM proxy is reachable
2. Check LITELLM_API_KEY has quota
3. Check network connection stability
4. Backend logs should show LLM errors

### Error: "Messages not saving to database"
**Solution:**
1. Check RLS policies are enabled
2. Verify user_id matches logged-in user
3. Check for database errors in backend logs
4. Run: `SELECT * FROM chat_messages;` in Supabase

---

## Monitoring Commands

### Check Active Connections
```sql
SELECT usename, application_name, state FROM pg_stat_activity 
WHERE datname = 'postgres';
```

### Check Message Count
```sql
SELECT COUNT(*) FROM chat_messages;
SELECT COUNT(*) FROM chat_threads;
SELECT COUNT(*) FROM profiles;
```

### Check Disk Usage
```sql
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Development Commands Reference

```bash
# Backend startup (with auto-reload)
uvicorn app.main:app --app-dir backend --reload

# Backend startup (production)
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

# Frontend development
cd frontend && npm run dev

# Frontend production build
cd frontend && npm run build
cd frontend && npm run preview

# Python syntax check
python -m compileall -q backend/app/

# Run migrations (if added later)
alembic upgrade head

# Database connection test
psql $DATABASE_URL -c "SELECT 1;"

# View backend logs (if saved to file)
tail -f backend.log
```

---

## API Quick Reference

```bash
# Sign up
curl -X POST http://127.0.0.1:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"Password123","full_name":"Test"}'

# Sign in
curl -X POST http://127.0.0.1:8000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"Password123"}'

# Get current user
curl "http://127.0.0.1:8000/api/auth/me?token=YOUR_TOKEN"

# List threads
curl "http://127.0.0.1:8000/api/threads?token=YOUR_TOKEN"

# Create thread
curl -X POST http://127.0.0.1:8000/api/threads?token=YOUR_TOKEN \
  -H "Content-Type: application/json" \
  -d '{"title":"New Thread"}'

# Send message (SSE stream)
curl -X POST http://127.0.0.1:8000/api/threads/THREAD_ID/messages?token=YOUR_TOKEN \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```
