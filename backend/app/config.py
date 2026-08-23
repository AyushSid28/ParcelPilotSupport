from pydantic_settings import BaseSettings, SettingsConfigDict

from app.paths import ROOT

GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    groq_api_key: str = ""
    groq_model: str = GROQ_MODEL
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def llm_key(self) -> str:
        return self.groq_api_key or self.openai_api_key

    @property
    def llm_base_url(self) -> str | None:
        if self.groq_api_key:
            return GROQ_BASE
        return self.openai_base_url or None

    @property
    def llm_model(self) -> str:
        if self.openai_model:
            return self.openai_model
        if self.groq_api_key:
            return self.groq_model
        return "gpt-4.1"

    @property
    def llm_provider(self) -> str:
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "none"


settings = Settings()
