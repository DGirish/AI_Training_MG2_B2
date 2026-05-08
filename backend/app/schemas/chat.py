from pydantic import BaseModel, Field
from uuid import UUID


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    attachment_ids: list[UUID] = Field(default_factory=list)
    generate_image: bool = False
