ALTER TABLE chat_attachments
ADD COLUMN IF NOT EXISTS indexed_status text DEFAULT 'not_indexed',
ADD COLUMN IF NOT EXISTS indexed_at timestamptz NULL,
ADD COLUMN IF NOT EXISTS chunk_count integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS indexing_error text NULL;
