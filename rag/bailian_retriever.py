from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from openai import OpenAI
from pydantic import Field

from agent.llm import normalize_model_name
from config.settings import settings


class BailianRetriever(BaseRetriever):
    api_key: str = Field(default_factory=lambda: settings.DASHSCOPE_API_KEY)
    base_url: str = Field(default_factory=lambda: settings.BAILIAN_COMPATIBLE_BASE_URL)
    knowledge_base_ids: list[str] = Field(default_factory=lambda: settings.bailian_knowledge_base_ids)
    knowledge_base_prompt: str = Field(default_factory=lambda: settings.BAILIAN_KNOWLEDGE_BASE_PROMPT)
    model: str = Field(default_factory=lambda: normalize_model_name(settings.DASHSCOPE_FAST or settings.DASHSCOPE_MODEL))
    top_k: int = 5

    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> list[Document]:
        if not self.api_key or not self.base_url or not self.knowledge_base_ids:
            return []

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": query}],
            extra_body={
                "knowledge_base_ids": self.knowledge_base_ids,
                "knowledge_base_prompt": self.knowledge_base_prompt,
                "top_k": self.top_k,
            },
        )

        answer = ""
        choices = getattr(response, "choices", None) or []
        if choices:
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            answer = getattr(message, "content", "") or ""

        if not answer:
            return []

        return [
            Document(
                page_content=answer,
                metadata={
                    "source": "bailian_rag_api",
                    "score": 1.0,
                    "knowledge_base_ids": self.knowledge_base_ids,
                },
            )
        ]

    async def _aget_relevant_documents(self, query: str, *, run_manager: Any = None) -> list[Document]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_relevant_documents, query)
