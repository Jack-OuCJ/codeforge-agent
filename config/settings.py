from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    DASHSCOPE_API_KEY: str = ""
    BAILIAN_APP_ID: str = ""
    BAILIAN_PIPELINE_ID: str = ""

    LLM_MODEL: str = "qwen-max"
    LLM_FAST: str = "qwen-turbo"
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 8192

    REQUIRE_APPROVAL_FOR_DELETE: bool = True
    REQUIRE_APPROVAL_FOR_WRITE_OUTSIDE_CWD: bool = True
    MAX_FILE_READ_SIZE_KB: int = 500

    MAX_ITERATIONS: int = 20
    MAX_CONTEXT_FILES: int = 30

    OPENAI_API_KEY: str = ""

    @model_validator(mode="after")
    def _fill_dashscope_key(self):
        if not self.DASHSCOPE_API_KEY and self.OPENAI_API_KEY:
            self.DASHSCOPE_API_KEY = self.OPENAI_API_KEY
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
