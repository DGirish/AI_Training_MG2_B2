from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

from app.schemas.thread import MessageResponse
from app.services.attachment_service import AttachmentService


class FakeDB:
    def __init__(self) -> None:
        self.added = []
        self.commit = AsyncMock()
        self.refresh = AsyncMock()

    def add(self, item) -> None:
        self.added.append(item)


class FakeBucket:
    def __init__(self) -> None:
        self.upload_calls = []

    def upload(self, path, content, options):
        self.upload_calls.append((path, content, options))


class FakeStorage:
    def __init__(self, bucket: FakeBucket) -> None:
        self.bucket = bucket

    def from_(self, _name: str) -> FakeBucket:
        return self.bucket


class AttachmentSchemaAndServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_message_response_coerces_null_attachment_fields(self) -> None:
        message = MessageResponse.model_validate(
            {
                "id": str(uuid4()),
                "role": "assistant",
                "content": "Generated an image for your prompt.",
                "attachment_ids": None,
                "attachments": None,
                "created_at": "2026-05-08T09:00:00Z",
            }
        )
        self.assertEqual(message.attachment_ids, [])
        self.assertEqual(message.attachments, [])

    async def test_create_generated_image_attachment_uploads_and_sets_metadata(self) -> None:
        service = AttachmentService()
        service._ensure_schema = AsyncMock()
        service._ensure_thread_access = AsyncMock()
        service._ensure_storage_bucket = AsyncMock()
        fake_bucket = FakeBucket()
        service._get_supabase_client = lambda: SimpleNamespace(storage=FakeStorage(fake_bucket))

        db = FakeDB()
        attachment = await service.create_generated_image_attachment(
            db,
            thread_id=uuid4(),
            user_id=uuid4(),
            source_message_id=uuid4(),
            prompt="Generate an image of a mountain lake",
            model_name="gemini/imagen-4.0-fast-generate-001",
            image_bytes=b"image-bytes",
            mime_type="image/png",
            file_name="generated-image.png",
            width=1024,
            height=1024,
        )

        self.assertEqual(attachment.attachment_type, "generated_image")
        self.assertEqual(attachment.model_name, "gemini/imagen-4.0-fast-generate-001")
        self.assertEqual(attachment.prompt, "Generate an image of a mountain lake")
        self.assertEqual(attachment.width, 1024)
        self.assertEqual(attachment.height, 1024)
        self.assertEqual(attachment.generation_status, "ready")
        self.assertTrue(fake_bucket.upload_calls)
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
