from __future__ import annotations

import asyncio
from typing import Any

from dashscope import Application
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from config.settings import settings


class BailianRetriever(BaseRetriever):
    app_id: str = Field(default_factory=lambda: settings.BAILIAN_APP_ID)
    api_key: str = Field(default_factory=lambda: settings.DASHSCOPE_API_KEY)
    pipeline_id: str = Field(default_factory=lambda: settings.BAILIAN_PIPELINE_ID)
    top_k: int = 5

    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> list[Document]:
        if not self.app_id or not self.api_key:
            return []

        response = Application.call(
            api_key=self.api_key,
            app_id=self.app_id,
            prompt=query,
            rag_options={
                "pipeline_ids": [self.pipeline_id] if self.pipeline_id else [],
                "top_k": self.top_k,
            },
        )

        docs: list[Document] = []
        if getattr(response, "status_code", None) == 200:
            references = getattr(response, "output", {}).get("doc_references", [])
            for ref in references:
                docs.append(
                    Document(
                        page_content=ref.get("content", ""),
                        metadata={
                            "source": ref.get("doc_name", ""),
                            "score": ref.get("score", 0.0),
                            "chunk_id": ref.get("chunk_id", ""),
                        },
                    )
                )
        return docs

    async def _aget_relevant_documents(self, query: str, *, run_manager: Any = None) -> list[Document]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_relevant_documents, query)
