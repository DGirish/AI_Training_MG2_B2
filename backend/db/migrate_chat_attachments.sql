-- Supabase SQL Editor migration: create chat_attachments and message attachment linkage
-- Safe to run multiple times.

BEGIN;

CREATE TABLE IF NOT EXISTS public.chat_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES public.chat_threads(id) ON DELETE CASCADE,
    message_id UUID NULL REFERENCES public.chat_messages(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL UNIQUE,
    public_url TEXT,
    mime_type TEXT NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size >= 0),
    attachment_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.chat_messages
    ADD COLUMN IF NOT EXISTS attachment_ids UUID[];

CREATE INDEX IF NOT EXISTS idx_chat_attachments_thread_id
    ON public.chat_attachments(thread_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_attachments_message_id
    ON public.chat_attachments(message_id);

CREATE INDEX IF NOT EXISTS idx_chat_attachments_user_id
    ON public.chat_attachments(user_id, created_at DESC);

ALTER TABLE public.chat_attachments ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'chat_attachments'
          AND policyname = 'Users can view own attachments'
    ) THEN
        CREATE POLICY "Users can view own attachments" ON public.chat_attachments
            FOR SELECT USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'chat_attachments'
          AND policyname = 'Users can insert own attachments'
    ) THEN
        CREATE POLICY "Users can insert own attachments" ON public.chat_attachments
            FOR INSERT WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'chat_attachments'
          AND policyname = 'Users can update own attachments'
    ) THEN
        CREATE POLICY "Users can update own attachments" ON public.chat_attachments
            FOR UPDATE USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'chat_attachments'
          AND policyname = 'Users can delete own attachments'
    ) THEN
        CREATE POLICY "Users can delete own attachments" ON public.chat_attachments
            FOR DELETE USING (auth.uid() = user_id);
    END IF;
END $$;

COMMIT;
