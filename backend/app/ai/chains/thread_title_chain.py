from __future__ import annotations

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.ai.llm import get_chat_llm


THREAD_TITLE_PROMPT = """You generate concise chat thread titles.
Create one short title (max 7 words) based on the user's first message.
Return only the title text with no quotes, numbering, or extra explanation.

User message:
{user_message}
"""


@lru_cache(maxsize=1)
def _get_prompt() -> PromptTemplate:
    return PromptTemplate.from_template(THREAD_TITLE_PROMPT)


def build_thread_title_chain():
    prompt = _get_prompt()
    llm = get_chat_llm()
    parser = StrOutputParser()
    return prompt | llm | parser
