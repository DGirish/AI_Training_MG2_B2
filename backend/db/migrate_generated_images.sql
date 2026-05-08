-- Supabase SQL Editor migration: extend chat_attachments for generated image assets
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.chat_attachments
    ADD COLUMN IF NOT EXISTS source_message_id UUID NULL REFERENCES public.chat_messages(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS storage_bucket TEXT NULL,
    ADD COLUMN IF NOT EXISTS model_name TEXT NULL,
    ADD COLUMN IF NOT EXISTS prompt TEXT NULL,
    ADD COLUMN IF NOT EXISTS width INTEGER NULL,
    ADD COLUMN IF NOT EXISTS height INTEGER NULL,
    ADD COLUMN IF NOT EXISTS generation_status TEXT NULL,
    ADD COLUMN IF NOT EXISTS generation_error TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_chat_attachments_source_message_id
    ON public.chat_attachments(source_message_id);

ALTER TABLE public.chat_attachments
    DROP CONSTRAINT IF EXISTS chat_attachments_attachment_type_check;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chat_attachments_generation_status_check'
    ) THEN
        ALTER TABLE public.chat_attachments
            ADD CONSTRAINT chat_attachments_generation_status_check
            CHECK (
                generation_status IS NULL
                OR generation_status IN ('pending', 'ready', 'failed')
            );
    END IF;
END $$;

INSERT INTO storage.buckets (id, name, public)
SELECT 'chat-assets', 'chat-assets', false
WHERE NOT EXISTS (
    SELECT 1 FROM storage.buckets WHERE id = 'chat-assets'
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Users can read own chat assets'
    ) THEN
        CREATE POLICY "Users can read own chat assets" ON storage.objects
            FOR SELECT USING (
                bucket_id = 'chat-assets'
                AND owner = auth.uid()
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Users can write own chat assets'
    ) THEN
        CREATE POLICY "Users can write own chat assets" ON storage.objects
            FOR INSERT WITH CHECK (
                bucket_id = 'chat-assets'
                AND owner = auth.uid()
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Users can update own chat assets'
    ) THEN
        CREATE POLICY "Users can update own chat assets" ON storage.objects
            FOR UPDATE USING (
                bucket_id = 'chat-assets'
                AND owner = auth.uid()
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Users can delete own chat assets'
    ) THEN
        CREATE POLICY "Users can delete own chat assets" ON storage.objects
            FOR DELETE USING (
                bucket_id = 'chat-assets'
                AND owner = auth.uid()
            );
    END IF;
END $$;

COMMIT;
