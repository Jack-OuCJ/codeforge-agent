from __future__ import annotations

import json

from langchain_community.chat_models import ChatTongyi

from config.settings import settings


def get_llm(temperature: float | None = None) -> ChatTongyi:
    return ChatTongyi(
        model=settings.LLM_MODEL,
        temperature=settings.TEMPERATURE if temperature is None else temperature,
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
    )


def parse_json_from_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise
