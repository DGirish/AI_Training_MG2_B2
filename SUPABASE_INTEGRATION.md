# Supabase Authentication & Chat Persistence - Integration Guide

## 1. Database Schema (SQL)

Located in `backend/db/schema.sql`

### Tables

#### `profiles` (synced with Supabase auth)
- `id` (UUID, PRIMARY KEY) - References auth.users(id)
- `email` (TEXT, UNIQUE) - Employee email
- `full_name` (TEXT, nullable) - Employee name
- `created_at` (TIMESTAMP) - Account creation time
- `updated_at` (TIMESTAMP) - Last update time

#### `chat_threads`
- `id` (UUID, PRIMARY KEY)
- `user_id` (UUID, FK) - References profiles(id)
- `title` (TEXT) - Thread name
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP) - Used for sorting recent threads

#### `chat_messages`
- `id` (UUID, PRIMARY KEY)
- `thread_id` (UUID, FK) - References chat_threads(id)
- `user_id` (UUID, FK) - References profiles(id)
- `role` (TEXT) - 'user' or 'assistant'
- `content` (TEXT) - Message body
- `created_at` (TIMESTAMP) - Used for chronological order

### Row Level Security (RLS)

All tables have RLS enabled to ensure users can only access their own data:
- Users can only view/edit their own profile
- Users can only access threads and messages they own

---

## 2. Backend Architecture

### New Modules

#### Database Layer (`backend/app/db/`)
- `session.py` - AsyncSessionLocal factory and get_db() dependency
- Uses async SQLAlchemy with asyncpg driver

#### Models (`backend/app/models/models.py`)
- `Profile` - Maps to auth.users via id
- `ChatThread` - User's chat thread
- `ChatMessage` - Individual messages in a thread

#### Services
- `auth_service.py` - Profile CRUD (sign_up, get_profile_by_email/id)
- `thread_service.py` - Thread CRUD and message persistence
  - `get_user_threads()` - Load all threads for user (sorted by recent)
  - `get_thread_by_id()` - Load specific thread with messages
  - `create_thread()` - New thread
  - `add_message()` - Persist user/assistant messages
- `persistent_chat_service.py` - End-to-end chat with persistence
  - `stream_chat_with_persistence()` - Stream LLM tokens while saving messages

#### API Routes
- `/api/auth/signup` - Create account
- `/api/auth/signin` - Login (returns JWT token)
- `/api/auth/me` - Get current user profile
- `/api/threads` - GET all threads, POST new thread
- `/api/threads/{thread_id}` - GET thread + messages, DELETE thread
- `/api/threads/{thread_id}/messages` - POST message (streams response)

### Config Updates
- Added `SECRET_KEY` setting for JWT signing
- Supports `DATABASE_URL` from `.env`

### Backward Compatibility
- Old `/api/chat` endpoint still works (for anonymous chats)
- Old `streamChat(message, handlers)` function signature supported
- LLM layer unchanged - still uses LiteLLM proxy via settings.LLM_MODEL

---

## 3. Frontend Architecture

### New Pages
- `LoginPage.tsx` - Sign up / Sign in UI
- `ChatPage.tsx` - Chat with sidebar showing thread history

### Auth Flow
1. User enters email/password on LoginPage
2. API returns JWT token + user profile
3. Token stored in localStorage
4. Passed in query param to all subsequent API calls

### Chat Flow
1. Load thread list on mount
2. Click thread → load messages for that thread
3. Type message → POST to `/api/threads/{threadId}/messages`
4. Response streams back via SSE (Server-Sent Events)
5. Messages auto-save to Supabase

### Updated API Client (`lib/api.ts`)
- `signUp()` - Create account
- `signIn()` - Login
- `getCurrentUser()` - Fetch current user
- `listThreads()` - Load all threads
- `createThread()` - New thread
- `getThread()` - Load thread + messages
- `deleteThread()` - Delete thread
- `streamChat(token, threadId, message, handlers)` - Persistent chat
- Backward-compatible `streamChat(message, handlers)` for legacy

### Updated Styling (`styles.css`)
- New `.auth-*` classes for login form
- New `.chat-layout` grid layout (sidebar + main)
- Sidebar for thread list with create/delete
- Thread selection + message display

---

## 4. Environment Variables

Add to `.env`:

```bash
# JWT signing (change in production!)
SECRET_KEY=your-secret-key-change-in-production

# Already in your .env:
DATABASE_URL=postgresql://...  # Supabase connection string
```

---

## 5. Setup Instructions

### Backend

1. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Run SQL schema on Supabase:**
   - Copy contents of `backend/db/schema.sql`
   - Run in Supabase SQL editor
   - Verify tables and RLS policies are created

3. **Start backend:**
   ```bash
   uvicorn app.main:app --app-dir backend --reload
   ```

### Frontend

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Run dev server:**
   ```bash
   npm run dev
   ```

3. **Build:**
   ```bash
   npm run build
   ```

---

## 6. User Flow

### Login
1. User navigates to app
2. LoginPage appears (sign up / sign in toggle)
3. Enter credentials
4. Backend validates, returns JWT
5. Frontend stores token, redirects to ChatPage

### Chat
1. ChatPage loads threads (GET `/api/threads`)
2. Click existing thread or create new one
3. View messages from that thread
4. Type message, hit Send
5. POST to `/api/threads/{threadId}/messages`
6. Backend:
   - Saves user message to DB
   - Calls LangChain chain (uses settings.LLM_MODEL)
   - Streams tokens back as SSE
   - Saves assistant response to DB
7. Frontend displays streamed tokens in real-time

### Logout
- Clear token from localStorage
- Redirect to LoginPage

---

## 7. Database Queries (Service Examples)

### Load user's threads (sorted by recent)
```python
stmt = (
    select(ChatThread)
    .where(ChatThread.user_id == user_id)
    .order_by(desc(ChatThread.updated_at))
    .options(selectinload(ChatThread.messages))
)
```

### Save message after streaming
```python
message = ChatMessage(
    thread_id=thread_id,
    user_id=user_id,
    role="assistant",
    content=full_response
)
db.add(message)
await db.commit()
```

---

## 8. Security Considerations

1. **RLS Enforced** - Supabase RLS policies prevent cross-user data access
2. **JWT Tokens** - Signed with SECRET_KEY, verified on every request
3. **Input Validation** - Pydantic schemas validate all inputs
4. **No Hardcoded Secrets** - All from `.env`
5. **LLM User Tracking** - Requests include user_email for audit

---

## 9. Troubleshooting

### "Module 'sqlalchemy' not found"
- Run `pip install -r backend/requirements.txt`

### "No token provided" / 401 errors
- Ensure token is passed in query param: `?token={access_token}`
- Check localStorage has token after login

### Messages not persisting
- Verify DATABASE_URL is set correctly
- Check RLS policies allow INSERT on chat_messages
- Verify user_id and thread_id match the authenticated user

### SSE stream stuck or timing out
- Check LiteLLM proxy is reachable (VPN access)
- Verify LITELLM_PROXY_URL and API key in .env
- Monitor backend logs for errors

---

## 10. LLM Integration (No Changes)

The chat streaming still uses:
- **LLM Model** - `settings.LLM_MODEL` (e.g., `gemini/gemini-2.5-flash`)
- **Gateway** - Amzur LiteLLM proxy at `settings.LITELLM_PROXY_URL`
- **Auth** - `settings.LITELLM_API_KEY`
- **Chain** - LCEL pipeline (prompt | llm | parser)

All existing prompts and chain logic remain unchanged. Persistence is added at the service layer without modifying AI calls.

---

## 11. Next Steps

- Test end-to-end: sign up → create thread → send message → verify message in DB
- Set up Supabase RLS policies in production
- Rotate SECRET_KEY in production `.env`
- Add email verification if needed
- Add password reset flow
- Add thread sharing/collaboration features
