from langchain_community.embeddings import DashScopeEmbeddings

from config.settings import settings


def get_embeddings() -> DashScopeEmbeddings:
    return DashScopeEmbeddings(
        model="text-embedding-v3",
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
    )
