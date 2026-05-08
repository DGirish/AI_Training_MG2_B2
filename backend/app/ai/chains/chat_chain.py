from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.ai.llm import get_chat_llm


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "chat_prompt.txt"


@lru_cache(maxsize=1)
def _get_prompt() -> PromptTemplate:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return PromptTemplate.from_template(template)


def build_chat_chain():
    prompt = _get_prompt()
    llm = get_chat_llm()
    parser = StrOutputParser()
    # Expects prompt variables: history, input, and attachment_context.
    return prompt | llm | parser
