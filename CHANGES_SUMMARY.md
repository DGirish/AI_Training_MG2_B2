# Backend & Frontend Changes Summary

## Files Added

### Backend

#### Database Schema
- `backend/db/schema.sql` - SQL migration for profiles, chat_threads, chat_messages tables with RLS

#### Database Layer
- `backend/app/db/session.py` - Async SQLAlchemy session factory and get_db() dependency

#### Models
- `backend/app/models/models.py` - SQLAlchemy ORM models (Profile, ChatThread, ChatMessage)

#### Services
- `backend/app/services/auth_service.py` - Profile management (sign_up, get_profile_by_email/id)
- `backend/app/services/thread_service.py` - Thread CRUD and message persistence
- `backend/app/services/persistent_chat_service.py` - End-to-end streaming chat with persistence

#### Authentication
- `backend/app/core/auth.py` - JWT token creation/validation, password hashing (bcrypt)

#### API Routes
- `backend/app/api/auth.py` - Auth endpoints (signup, signin, me)
- `backend/app/api/threads.py` - Thread CRUD endpoints
- `backend/app/api/persistent_chat.py` - Chat with message persistence endpoint

#### Schemas
- `backend/app/schemas/auth.py` - Pydantic models for auth requests/responses
- `backend/app/schemas/thread.py` - Pydantic models for threads and messages

### Frontend

#### Pages
- `frontend/src/pages/LoginPage.tsx` - Sign up / Sign in UI
- `frontend/src/pages/ChatPage.tsx` - Chat interface with thread sidebar

#### Types
- `frontend/src/types/index.ts` - Consolidated chat, user, and auth types
- `frontend/src/types/auth.ts` - Auth-specific types (can be merged into index.ts)

#### Updated Files
- `frontend/src/lib/api.ts` - Added auth, thread, and persistent chat API methods
- `frontend/src/App.tsx` - Auth routing logic
- `frontend/src/styles.css` - New auth and chat layout styles

---

## Files Updated

### Backend
- `backend/app/main.py` - Added routers: auth, threads, persistent_chat
- `backend/app/core/config.py` - Added SECRET_KEY setting
- `backend/requirements.txt` - Added: sqlalchemy, psycopg, alembic, supabase, python-jose, passlib

### Frontend
- None major changes beyond replacements above

---

## Key Design Decisions

1. **Service Layer** - All business logic in services, routers only parse/validate
2. **JWT Tokens** - Passed in query param (? token=...) since these are SSE streams
3. **Async SQLAlchemy** - Used async for consistency with FastAPI async handlers
4. **Backward Compatibility** - Old /api/chat endpoint still works for legacy clients
5. **No Hardcoded Secrets** - All from .env

---

## Known Issues / Not Yet Implemented

### 1. Database URL Needs Async Dialect
**Issue**: Current code assumes `DATABASE_URL` is standard PostgreSQL format
**Fix Needed**: Update `database_url` in config to use async dialect (asyncpg):
```python
# In config.py - modify if DATABASE_URL is present
database_url: str | None = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
```

### 2. RLS Policies Use auth.uid()
**Issue**: Supabase RLS uses `auth.uid()` function which may not work with regular JWT
**Action**: Test RLS after running schema.sql; may need to adjust if using custom JWT

### 3. Password Hashing Not Used in signIn
**Issue**: Current signin doesn't verify password (schema doesn't have password column)
**Fix Needed**: Add password storage to profiles table OR use Supabase Auth service for passwords

### 4. Token Expiry Not Enforced
**Issue**: JWT tokens don't refresh, only expire after 24 hours
**Improvement**: Add refresh token logic if needed for longer sessions

### 5. Query Params on SSE Requests
**Issue**: Token in query param `?token=...` could be logged in access logs
**Improvement**: Use Authorization header if frontend can support it for streaming

### 6. Missing Auth Error Detail
**Issue**: Some auth errors don't specify which field failed (email/password)
**Improvement**: Return structured error response

---

## Setup Checklist Before Running

- [ ] 1. Update .env:
  - [ ] Add `SECRET_KEY=your-secret-key-change-me`
  - [ ] Verify `DATABASE_URL` is Supabase PostgreSQL connection string
  
- [ ] 2. Update backend config.py:
  - [ ] Modify `database_url` to convert postgresql:// to postgresql+asyncpg://
  
- [ ] 3. Create database tables:
  - [ ] Open Supabase SQL editor
  - [ ] Copy `backend/db/schema.sql` and run it
  - [ ] Verify profiles, chat_threads, chat_messages exist
  - [ ] Verify RLS policies are created
  
- [ ] 4. Install backend dependencies:
  - [ ] Run `pip install -r backend/requirements.txt`
  
- [ ] 5. Test backend startup:
  - [ ] Run `uvicorn app.main:app --app-dir backend --reload`
  - [ ] Verify /health returns 200 OK
  
- [ ] 6. Install frontend dependencies:
  - [ ] Run `npm install` in frontend/
  
- [ ] 7. Test frontend build:
  - [ ] Run `npm run build` in frontend/
  - [ ] Should complete with no errors
  
- [ ] 8. Run frontend dev server:
  - [ ] Run `npm run dev` in frontend/
  - [ ] Visit http://127.0.0.1:5173
  - [ ] Should see LoginPage
  
- [ ] 9. Test signup:
  - [ ] Enter email/password/name
  - [ ] Should create profile in Supabase
  - [ ] Should return token and redirect to ChatPage
  
- [ ] 10. Test chat:
  - [ ] Click "+ New Thread"
  - [ ] Enter title, create thread
  - [ ] Type message and send
  - [ ] Verify message appears and streams
  - [ ] Check Supabase chat_messages table for saved messages

---

## API Endpoints

### Authentication
- POST `/api/auth/signup` - Create account
- POST `/api/auth/signin` - Login
- GET `/api/auth/me?token={token}` - Current user

### Threads
- GET `/api/threads?token={token}` - List threads
- POST `/api/threads?token={token}` - Create thread
- GET `/api/threads/{thread_id}?token={token}` - Get thread + messages
- DELETE `/api/threads/{thread_id}?token={token}` - Delete thread

### Chat
- POST `/api/threads/{thread_id}/messages?token={token}` - Send message (SSE stream)
- POST `/api/chat` - Legacy chat (no auth, no persistence)

---

## Data Flow Diagram

```
Frontend (React)
  ↓
LoginPage → /api/auth/signup/signin → returns JWT
  ↓
ChatPage (receives JWT + user)
  ├─ Load threads: GET /api/threads?token=...
  │   ↓
  │   ThreadService.get_user_threads()
  │   ↓
  │   SELECT * FROM chat_threads WHERE user_id = {...}
  │
  ├─ Select thread
  │   ↓
  │   Display messages from ChatThread.messages
  │
  ├─ Send message
  │   ↓
  │   POST /api/threads/{id}/messages?token=...
  │   ↓
  │   PersistentChatService.stream_chat_with_persistence()
  │   ├─ Save user message: INSERT INTO chat_messages
  │   ├─ Call LLM via LangChain chain (uses settings.LLM_MODEL)
  │   ├─ Stream tokens back as SSE events
  │   └─ Save assistant response: INSERT INTO chat_messages
  │
  └─ Logout
      ↓
      Clear localStorage token
      ↓
      Redirect to LoginPage
```

---

## Testing Queries for Supabase

After signup/signin and creating a thread with messages:

```sql
-- View all profiles
SELECT * FROM profiles;

-- View user's threads
SELECT * FROM chat_threads WHERE user_id = '...user-id...';

-- View messages in a thread
SELECT * FROM chat_messages WHERE thread_id = '...thread-id...' ORDER BY created_at;

-- Count messages by role
SELECT role, COUNT(*) FROM chat_messages GROUP BY role;
```

---

## Production Checklist

- [ ] Change SECRET_KEY to a long random string
- [ ] Enable HTTPS on backend
- [ ] Set FRONTEND_ORIGIN to actual domain
- [ ] Configure Supabase RLS policies for production access levels
- [ ] Add email verification
- [ ] Add password reset
- [ ] Set up logging/monitoring
- [ ] Add rate limiting on auth endpoints
- [ ] Add CORS configuration for specific origins (not wildcard)
- [ ] Test database backups
