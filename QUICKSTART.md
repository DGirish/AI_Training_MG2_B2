# Quick Start Guide

## ⏱️ 5 Minute Setup

### 1. Update .env
```bash
# In project root directory
echo "SECRET_KEY=your-secret-key-change-me-must-be-32-chars-minimum" >> .env
echo "DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db" >> .env
```

### 2. Run Database Migration
Copy contents of `backend/db/schema.sql` and run in Supabase SQL editor.

### 3. Install Backend
```bash
pip install -r requirements.txt
```

### 4. Install Frontend
```bash
cd frontend && npm install
```

### 5. Start Backend (Terminal 1)
```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat"
uvicorn app.main:app --app-dir backend --reload
# Opens on http://127.0.0.1:8000
```

### 6. Start Frontend (Terminal 2)
```bash
cd "d:\. AI Forge Training\backend\Stackyon Intelligent Chat\frontend"
npm run dev
# Opens on http://127.0.0.1:5173
```

### 7. Open Browser
Navigate to http://127.0.0.1:5173 and test signup/signin!

---

## 🧪 Quick Test

1. Sign up: `test@example.com` / `Password123` / `Test User`
2. Create thread: `My First Thread`
3. Send message: `Hello, how are you?`
4. Verify it streams back and saves to database

---

## 📋 Verify Setup

```bash
# Check backend is running
curl http://127.0.0.1:8000/health

# Check frontend is built
curl http://127.0.0.1:5173

# Check database connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM profiles;"
```

---

## 🔧 Troubleshooting

| Error | Fix |
|-------|-----|
| `uvicorn: command not found` | Run `pip install -r requirements.txt` |
| `DATABASE_URL not found` | Add to `.env`: `DATABASE_URL=...` |
| `npm: command not found` | Install Node.js from nodejs.org |
| `TypeScript errors on build` | Run `cd frontend && npm install` |
| `CORS error in browser` | Restart backend after .env update |

---

## 📚 Full Documentation

- **[SUPABASE_INTEGRATION.md](SUPABASE_INTEGRATION.md)** - Architecture & APIs
- **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)** - All files added/changed
- **[TESTING_DEPLOYMENT.md](TESTING_DEPLOYMENT.md)** - Complete testing guide
- **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** - Status & next steps

---

## 🚀 Deploy to Production

```bash
# Build frontend
cd frontend && npm run build

# Set production environment variables
$env:SECRET_KEY = "long-random-32-char-string"
$env:DATABASE_URL = "production-postgresql-url"
$env:LITELLM_PROXY_URL = "https://litellm.amzur.com/v1"
$env:LITELLM_API_KEY = "your-litellm-key"

# Start backend on production port
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

# Serve frontend with nginx/apache or upload to CDN
# Contents of frontend/dist/
```

---

## 💡 Key Endpoints

```bash
# Sign up
curl -X POST http://127.0.0.1:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"Pass123","full_name":"User"}'

# Sign in
curl -X POST http://127.0.0.1:8000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"Pass123"}'

# List threads
curl "http://127.0.0.1:8000/api/threads?token=JWT_TOKEN_HERE"

# Send message (streams SSE)
curl -X POST "http://127.0.0.1:8000/api/threads/THREAD_ID/messages?token=JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

---

## 📱 Feature Checklist

- ✅ User signup with email/password
- ✅ User signin with JWT token
- ✅ Create chat threads
- ✅ Send messages to AI
- ✅ Stream responses in real-time
- ✅ Save messages to PostgreSQL
- ✅ Load chat history
- ✅ Delete threads
- ✅ Support multiple users with RLS
- ✅ Logout and login again

---

**Need help?** See [TESTING_DEPLOYMENT.md](TESTING_DEPLOYMENT.md) for detailed troubleshooting!
