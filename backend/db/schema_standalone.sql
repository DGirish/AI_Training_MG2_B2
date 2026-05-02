-- ============================================================
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
