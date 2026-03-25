from __future__ import annotations

import json

from langchain_openai import ChatOpenAI

from config.settings import settings


def normalize_model_name(model_name: str) -> str:
    if not model_name:
        return "qwen-plus"
    return model_name.strip()


def get_llm(temperature: float | None = None) -> ChatOpenAI:
    provider = settings.LLM_PROVIDER
    if provider == "minimax":
        return ChatOpenAI(
            model=settings.MINIMAX_MODEL,
            temperature=settings.TEMPERATURE if temperature is None else temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.MINIMAX_API_KEY,
            base_url=settings.MINIMAX_BASE_URL,
            streaming=True,
        )
    # 默认 dashscope (阿里百炼)
    return ChatOpenAI(
        model=normalize_model_name(settings.DASHSCOPE_MODEL),
        temperature=settings.TEMPERATURE if temperature is None else temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.BAILIAN_COMPATIBLE_BASE_URL,
        streaming=True,
    )


def get_fast_llm(temperature: float | None = None) -> ChatOpenAI:
    """获取快速模型（用于简单任务）"""
    provider = settings.LLM_PROVIDER
    if provider == "minimax":
        return ChatOpenAI(
            model=settings.MINIMAX_FAST,
            temperature=settings.TEMPERATURE if temperature is None else temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.MINIMAX_API_KEY,
            base_url=settings.MINIMAX_BASE_URL,
            streaming=True,
        )
    return ChatOpenAI(
        model=normalize_model_name(settings.DASHSCOPE_FAST),
        temperature=settings.TEMPERATURE if temperature is None else temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.BAILIAN_COMPATIBLE_BASE_URL,
        streaming=True,
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
