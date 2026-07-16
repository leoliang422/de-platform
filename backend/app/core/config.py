from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    database_url: str = "postgresql+asyncpg://de:de@localhost:5432/de_platform"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "mock"
    payment_provider: str = "mock"

    # 投稿加工是否走 ARQ 异步队列；本地演示默认关闭（同一请求内同步加工）。
    task_queue_enabled: bool = False

    # 豆包（火山方舟 Ark，OpenAI 兼容）；无 key 时回退 MockLLM。
    doubao_api_key: str = ""
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-pro-4k"

    # 生产用逗号分隔的字符串配置，例如：
    #   CORS_ORIGINS=https://xxx.vercel.app,https://www.example.com
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
