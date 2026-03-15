from __future__ import annotations

from langchain_core.tools import tool

from rag.bailian_retriever import BailianRetriever


retriever = BailianRetriever()


@tool
async def rag_retrieve(query: str) -> str:
    """从知识库中检索与编程任务相关的文档、API 文档、代码示例。"""
    docs = await retriever._aget_relevant_documents(query)
    if not docs:
        return "知识库中未找到相关内容"

    lines = [f"找到 {len(docs)} 条相关文档：", ""]
    for index, doc in enumerate(docs, 1):
        lines.append(f"[{index}] 来源: {doc.metadata.get('source', '')}")
        lines.append(f"相关度: {doc.metadata.get('score', 0.0):.2f}")
        lines.append("内容:")
        lines.append(doc.page_content)
        lines.append("---")
    return "\n".join(lines)
