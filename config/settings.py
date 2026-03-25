from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    # LLM Provider: "dashscope" or "minimax"
    LLM_PROVIDER: str = "dashscope"

    # DashScope (阿里百炼) 配置
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_HTTP_API_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    BAILIAN_COMPATIBLE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODEL: str = "qwen3-max"
    DASHSCOPE_FAST: str = "qwen3-max"

    # MiniMax 配置
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = "https://api.minimax.chat/v1"
    MINIMAX_MODEL: str = "MiniMax-M2.7"
    MINIMAX_FAST: str = "MiniMax-M2.7"

    # 百炼知识库 RAG 配置
    BAILIAN_KNOWLEDGE_BASE_IDS: str = ""
    BAILIAN_KNOWLEDGE_BASE_PROMPT: str = "请基于知识库回答"
    ENABLE_RAG: bool = True
    RAG_USE_MODEL_GATE: bool = True

    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 0

    REQUIRE_APPROVAL_FOR_DELETE: bool = True
    REQUIRE_APPROVAL_FOR_WRITE_OUTSIDE_CWD: bool = True
    MAX_FILE_READ_SIZE_KB: int = 500

    MAX_ITERATIONS: int = 20
    MAX_CONTEXT_FILES: int = 30
    ROUTER_NAME: str = "rule_based_router"

    SHOW_DEBUG_STREAM: bool = False
    SHOW_MODEL_THINK: bool = False
    CHAT_DISPLAY_MAX_RENDER_LINES: int = 1200
    TOOL_OUTPUT_DISPLAY_MAX_CHARS: int = 0
    TOOL_OUTPUT_MODEL_MAX_CHARS: int = 0

    OPENAI_API_KEY: str = ""

    @property
    def bailian_knowledge_base_ids(self) -> list[str]:
        if not self.BAILIAN_KNOWLEDGE_BASE_IDS:
            return []
        raw = self.BAILIAN_KNOWLEDGE_BASE_IDS.replace("\n", ",")
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def llm_max_tokens(self) -> int | None:
        value = int(self.MAX_TOKENS)
        if value <= 0:
            return None
        return value

    @model_validator(mode="after")
    def _fill_dashscope_key(self):
        if not self.DASHSCOPE_API_KEY and self.OPENAI_API_KEY:
            self.DASHSCOPE_API_KEY = self.OPENAI_API_KEY
        if self.DASHSCOPE_BASE_HTTP_API_URL:
            normalized = self.DASHSCOPE_BASE_HTTP_API_URL.strip().rstrip("/")
            if normalized.endswith("/compatible-mode/v1"):
                normalized = normalized[: -len("/compatible-mode/v1")] + "/api/v1"
            self.DASHSCOPE_BASE_HTTP_API_URL = normalized
        if self.BAILIAN_COMPATIBLE_BASE_URL:
            compatible = self.BAILIAN_COMPATIBLE_BASE_URL.strip().rstrip("/")
            if compatible.endswith("/api/v1"):
                compatible = compatible[: -len("/api/v1")] + "/compatible-mode/v1"
            self.BAILIAN_COMPATIBLE_BASE_URL = compatible
        return self

    model_config = SettingsConfigDict(env_file=(".env", "config/.env"), env_file_encoding="utf-8", extra="ignore")


settings = Settings()
