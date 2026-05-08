# Project File Reference

## 📁 Root Level

### Documentation (READ THESE FIRST)
- **QUICKSTART.md** ← START HERE - 5 minute setup guide
- **SUPABASE_INTEGRATION.md** - Full architecture, schema, and API reference
- **CHANGES_SUMMARY.md** - All files added/changed in Phase 3
- **TESTING_DEPLOYMENT.md** - Complete testing procedures and troubleshooting
- **IMPLEMENTATION_COMPLETE.md** - Status, what's ready, next steps

### Configuration
- **.env** - Environment variables (add SECRET_KEY and DATABASE_URL)
- **copilot-instructions.md** - Original project instructions
- **prompt-instructions.md** - Original prompt notes
- **requirements.txt** - Python dependencies (shared/legacy)

---

## 🔧 Backend Files

### Entry Point
- **backend/app/main.py** - FastAPI app initialization
  - Registers all routers (auth, threads, persistent_chat)
  - Sets up CORS middleware
  - Includes health check endpoint

### Configuration & Auth
- **backend/app/core/config.py** - Environment settings loader
  - Loads all .env variables
  - Database URL conversion to async dialect
  - FRONTEND_ORIGIN parsing (comma-separated)
  
- **backend/app/core/auth.py** - JWT and password utilities
  - `hash_password()` - Bcrypt hashing
  - `verify_password()` - Bcrypt verification
  - `create_access_token()` - Generate JWT tokens
  - `decode_token()` - Validate JWT tokens
  - `get_current_user_from_db()` - Get user from token

### Database Layer
- **backend/app/db/session.py** - SQLAlchemy async session factory
  - `engine` - Async engine with asyncpg driver
  - `AsyncSessionLocal` - Session factory
  - `get_db()` - FastAPI dependency injection

- **backend/app/models/models.py** - SQLAlchemy ORM models
  - `Profile` - User account (maps to auth.users)
  - `ChatThread` - Conversation thread
  - `ChatMessage` - Individual message in thread

### Business Logic
- **backend/app/services/auth_service.py** - Authentication service
  - `sign_up()` - Create new user profile
  - `get_profile_by_email()` - Lookup user by email
  - `get_profile_by_id()` - Lookup user by ID

- **backend/app/services/thread_service.py** - Thread management
  - `get_user_threads()` - Load all threads for user (sorted by recent)
  - `get_thread_by_id()` - Load specific thread with messages
  - `create_thread()` - Create new thread
  - `add_message()` - Save message to thread

- **backend/app/services/persistent_chat_service.py** - Streaming with persistence
  - `stream_chat_with_persistence()` - Stream LLM tokens while saving messages
  - Saves user message, streams response, saves assistant response

### Validation Schemas
- **backend/app/schemas/auth.py** - Auth request/response models
  - `SignUpRequest` - Email, password, full_name
  - `SignInRequest` - Email, password
  - `AuthResponse` - Access token + user profile
  - `ProfileResponse` - User data

- **backend/app/schemas/thread.py** - Thread request/response models
  - `ThreadCreate` - Thread creation
  - `ThreadResponse` - Thread with messages
  - `MessageResponse` - Message data
  - `MessageCreate` - Message content

### API Routes
- **backend/app/api/auth.py** - Authentication endpoints
  - `POST /api/auth/signup` - Create account
  - `POST /api/auth/signin` - Login, returns JWT
  - `GET /api/auth/me` - Get current user

- **backend/app/api/threads.py** - Thread management endpoints
  - `GET /api/threads` - List all threads
  - `POST /api/threads` - Create new thread
  - `GET /api/threads/{id}` - Get thread with messages
  - `DELETE /api/threads/{id}` - Delete thread

- **backend/app/api/persistent_chat.py** - Chat with persistence
  - `POST /api/threads/{id}/messages` - Send message (SSE stream)
  - Handles auth, streams response, saves messages

### LLM Integration (Unchanged from Phase 1)
- **backend/app/ai/chains.py** - LangChain chat chain
  - `build_chat_chain()` - Creates LCEL pipeline
  - Uses settings.LLM_MODEL via LiteLLM proxy
  - Unchanged from original implementation

- **backend/app/ai/prompt.md** - System prompt for AI
  - Defines chatbot behavior
  - Can be customized for different use cases

### Database Migration
- **backend/db/schema.sql** - PostgreSQL schema creation
  - `profiles` table (user data)
  - `chat_threads` table (conversations)
  - `chat_messages` table (individual messages)
  - RLS policies for data isolation
  - Indexes for performance

---

## 🎨 Frontend Files

### Entry Points
- **frontend/index.html** - HTML shell
  - References React root div
  - Loads built app.js

- **frontend/src/main.tsx** - React entry point
  - Renders App component

### Core App Component
- **frontend/src/App.tsx** - Main routing and auth logic
  - Shows LoginPage if no token
  - Shows ChatPage if authenticated
  - Handles logout

### Pages
- **frontend/src/pages/LoginPage.tsx** - Authentication UI
  - Toggle between sign up and sign in
  - Form handling and validation
  - Calls auth functions from api.ts
  - Redirects to ChatPage on success

- **frontend/src/pages/ChatPage.tsx** - Main chat interface
  - Sidebar with thread list
  - Message display area
  - Input form for new messages
  - Thread creation/deletion
  - SSE streaming handler

### API Client
- **frontend/src/lib/api.ts** - All backend API calls
  - `signUp(email, password, fullName)` - Create account
  - `signIn(email, password)` - Login
  - `getCurrentUser(token)` - Get current user
  - `listThreads(token)` - Load all threads
  - `createThread(token, title)` - New thread
  - `getThread(token, threadId)` - Load thread + messages
  - `deleteThread(token, threadId)` - Delete thread
  - `streamChat(token, threadId, message, handlers)` - Persistent chat
  - `streamChat(message, handlers)` - Legacy chat (no auth)
  - All modern calls use token query param

### Types & Configuration
- **frontend/src/types/index.ts** - Main type definitions
  - `User` - User profile
  - `ChatMessage` - Message with role
  - `ChatThread` - Thread with messages
  - `ChatRole` - 'user' | 'assistant'
  - `AuthResponse` - Login response

- **frontend/src/types/auth.ts** - Auth-specific types
  - `AuthResponse` interface (can be merged into index.ts)

- **frontend/src/config/env.ts** - Frontend configuration
  - `API_BASE_URL` - Backend URL (defaults to http://127.0.0.1:8000)
  - Can be overridden in .env.local

### Styling
- **frontend/src/styles.css** - All application styles
  - `.auth-container` / `.auth-card` - Login form layout
  - `.chat-layout` - Grid layout (sidebar + main)
  - `.chat-sidebar` - Thread list styling
  - `.chat-main` - Messages and input area
  - Responsive design for mobile

### Build Configuration
- **frontend/package.json** - Dependencies and scripts
  - `npm run dev` - Development server (Vite)
  - `npm run build` - Production build (TypeScript + Vite)
  - `npm run preview` - Preview production build

- **frontend/tsconfig.json** - TypeScript configuration
  - Strict mode enabled
  - React JSX setup
  - ES2020 target

- **frontend/vite.config.ts** - Vite build configuration
  - React plugin enabled
  - Development server settings

---

## 🗂️ File Organization Summary

### Backend Structure
```
backend/
├── app/
│   ├── core/           ← Configuration & Auth
│   ├── db/             ← Database session management
│   ├── models/         ← SQLAlchemy ORM models
│   ├── schemas/        ← Pydantic validation
│   ├── services/       ← Business logic layer
│   ├── api/            ← HTTP route handlers
│   ├── ai/             ← LLM integration (unchanged)
│   └── main.py         ← App entry point
├── db/
│   └── schema.sql      ← Database migration
└── requirements.txt    ← Python dependencies
```

### Frontend Structure
```
frontend/
├── src/
│   ├── pages/          ← LoginPage, ChatPage
│   ├── lib/            ← API client, utilities
│   ├── types/          ← TypeScript interfaces
│   ├── config/         ← Environment settings
│   ├── styles.css      ← All styling
│   ├── App.tsx         ← Main routing
│   └── main.tsx        ← React entry
├── dist/               ← Production build output
├── package.json        ← Dependencies
└── vite.config.ts      ← Build config
```

---

## 📊 Data Flow

```
User Browser
    ↓
Frontend (React + TypeScript)
    ├─ LoginPage → Sign up/in
    ├─ ChatPage → View threads + send messages
    └─ api.ts → Makes HTTP calls
    ↓
Backend (FastAPI)
    ├─ /api/auth/* → auth_service.py → models (Profile)
    ├─ /api/threads/* → thread_service.py → models (ChatThread, ChatMessage)
    └─ /api/threads/{id}/messages → persistent_chat_service.py
    ↓
PostgreSQL (Supabase)
    ├─ profiles table (user data)
    ├─ chat_threads table (conversations)
    └─ chat_messages table (individual messages)
```

---

## 🔑 Key Constants

### Backend
- JWT Algorithm: `HS256`
- JWT Expiry: `24 hours`
- Password Hash: `bcrypt`
- Database Driver: `asyncpg`
- CORS: From `FRONTEND_ORIGIN` env var

### Frontend
- API Base: `http://127.0.0.1:8000` (dev) or from env
- Token Storage: `localStorage['token']`
- SSE Event Parsing: Real newlines (not escaped)

### Database
- RLS: Enabled on all tables
- UUID Type: PostgreSQL native UUID
- Indexes: On user_id, thread_id (foreign keys)
- Cascade: Delete profile → delete threads → delete messages

---

## 🧪 Testing Reference

### Backend Health Check
```bash
curl http://127.0.0.1:8000/health
# Returns: {"status":"ok"}
```

### Sign Up
```bash
curl -X POST http://127.0.0.1:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass123","full_name":"Test"}'
```

### Send Message
```bash
curl -X POST "http://127.0.0.1:8000/api/threads/THREAD_ID/messages?token=JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

---

## 📝 Notes

- All files follow clean architecture principles
- Service layer contains business logic
- Routers only handle HTTP concerns
- Database access only through services
- Type safety enforced with TypeScript and Pydantic
- Backward compatible with Phase 1 & 2 features
- No hardcoded secrets (all from .env)
- Ready for production deployment

---

**Start with QUICKSTART.md for setup instructions!**
