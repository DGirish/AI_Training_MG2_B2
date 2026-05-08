# Stackyon Intelligent Chat

Stackyon Intelligent Chat is a FastAPI + React application for threaded AI conversations with email/password authentication, Google sign-in, Supabase/PostgreSQL persistence, prior-conversation memory, file attachments, and Gemini-backed chat generation through the Amzur LiteLLM proxy.

## Image Generation

Project 6 extends the existing attachment-driven chat architecture instead of replacing it.

- Users can switch the chat composer into image generation mode and submit a prompt directly from the existing chat window.
- The backend uses the required image model `gemini/imagen-4.0-fast-generate-001` through the existing LiteLLM/OpenAI-compatible proxy pattern.
- Generated images are persisted as enriched `chat_attachments` records and linked to both the prompt message and the assistant message in the same thread.
- Generated image bytes are uploaded to Supabase Storage in the private `chat-assets` bucket.
- Thread reloads show previously generated images through the normal message history path.
- Existing text chat, auth, threads, auto-naming, memory, and file attachment flows remain in place.

## How It Works

1. The user enters a prompt in the existing composer and enables image generation mode.
2. The backend stores the user prompt as a normal chat message.
3. `PersistentChatService` detects the image-generation request and routes it to `ImageGenerationService`.
4. `ImageGenerationService` calls `gemini/imagen-4.0-fast-generate-001` via LiteLLM.
5. The returned image bytes are stored in Supabase Storage and metadata is saved in PostgreSQL by extending the existing `chat_attachments` table.
6. The assistant reply is saved as a normal assistant message whose attachments include the generated image.
7. The frontend renders the generated image inline via the authenticated attachment content endpoint.

## Required Environment Variables

Use `.env.example` as the reference template.

Core AI and storage settings for image generation:

- `LITELLM_PROXY_URL`
- `LITELLM_API_KEY`
- `LLM_MODEL`
- `IMAGE_GEN_MODEL=gemini/imagen-4.0-fast-generate-001`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET=chat-assets`
- `DATABASE_URL` or `DATABASE_POOLER_URL`

## Storage and Persistence

- Uploaded user files continue to use the existing attachment flow.
- Generated images are stored in Supabase Storage rather than as database blobs.
- Metadata is stored in PostgreSQL by extending `chat_attachments` with generation-specific fields such as prompt, model name, status, bucket, and source message linkage.
- Secure rendering is handled through the backend attachment content route so storage objects do not need to be public.

## Migrations

Run the existing attachment migration first if needed, then apply the generated-image extension SQL in:

- `backend/db/migrate_chat_attachments.sql`
- `backend/db/migrate_generated_images.sql`

## Implementation Notes

This feature was added by analyzing and extending the current codebase rather than replacing it.

- Reused the existing `chat_attachments` table instead of creating a separate asset table.
- Reused the existing thread/message persistence flow instead of introducing a parallel chat subsystem.
- Reused the existing chat streaming endpoint by adding a backward-compatible `generate_image` flag.
- Reused the existing chat history UI by rendering generated images as normal assistant-message attachments.

## Local Development

Backend:

```powershell
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
