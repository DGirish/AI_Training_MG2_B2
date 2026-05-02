from __future__ import annotations

from app.ai.chains.thread_title_chain import build_thread_title_chain


MAX_FALLBACK_TITLE_LEN = 40


class ThreadNamingService:
    async def generate_title(self, first_message: str) -> str:
        fallback_title = self._fallback_title(first_message)

        try:
            chain = build_thread_title_chain()
            candidate = await chain.ainvoke({"user_message": first_message})
            cleaned = self._clean_title(candidate)
            return cleaned or fallback_title
        except Exception:
            return fallback_title

    @staticmethod
    def _fallback_title(message: str) -> str:
        text = " ".join(message.strip().split())
        if not text:
            return "New Chat"
        if len(text) <= MAX_FALLBACK_TITLE_LEN:
            return text
        return f"{text[:MAX_FALLBACK_TITLE_LEN].rstrip()}..."

    @staticmethod
    def _clean_title(raw_title: str) -> str:
        title = " ".join((raw_title or "").strip().split())
        title = title.strip("\"'")
        if len(title) > 80:
            title = title[:80].rstrip()
        return title
