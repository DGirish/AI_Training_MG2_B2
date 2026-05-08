from __future__ import annotations

from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.core.config import settings


def get_chat_llm() -> ChatOpenAI:
    if not settings.litellm_proxy_url:
        raise ValueError("Missing LITELLM_PROXY_URL in environment")
    if not settings.litellm_api_key:
        raise ValueError("Missing LITELLM_API_KEY or LITELLM_VIRTUAL_KEY in environment")

    return ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.litellm_proxy_url,
        api_key=settings.litellm_api_key,
        streaming=True,
        timeout=30,
        max_retries=2,
    )


def get_litellm_openai_client() -> OpenAI:
    if not settings.litellm_proxy_url:
        raise ValueError("Missing LITELLM_PROXY_URL in environment")
    if not settings.litellm_api_key:
        raise ValueError("Missing LITELLM_API_KEY or LITELLM_VIRTUAL_KEY in environment")

    return OpenAI(
        api_key=settings.litellm_api_key,
        base_url=settings.litellm_proxy_url,
        timeout=60,
        max_retries=2,
    )
