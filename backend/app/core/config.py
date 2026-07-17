from functools import lru_cache

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
    # 支付通道：mock（默认，同步结算）| wechat | alipay。
    # 选 wechat/alipay 但凭证未配齐时，工厂会自动回退到 mock（见 payment/provider.py）。
    payment_provider: str = "mock"

    # ---- 微信支付（v3 Native）占位配置；获取方式见 docs/deployment.md ----
    wechat_app_id: str = ""
    wechat_mch_id: str = ""
    wechat_api_v3_key: str = ""
    wechat_cert_serial: str = ""
    wechat_private_key_path: str = ""
    wechat_notify_url: str = ""

    # ---- 支付宝（电脑/手机网站支付）占位配置；获取方式见 docs/deployment.md ----
    alipay_app_id: str = ""
    alipay_private_key: str = ""
    alipay_public_key: str = ""
    alipay_gateway: str = "https://openapi.alipay.com/gateway.do"
    alipay_notify_url: str = ""

    # 投稿加工是否走 ARQ 异步队列；本地演示默认关闭（同一请求内同步加工）。
    task_queue_enabled: bool = False

    # 豆包（火山方舟 Ark，OpenAI 兼容）；无 key 时回退 MockLLM。
    doubao_api_key: str = ""
    doubao_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-pro-4k"

    # 逗号分隔的允许来源，例如：
    #   CORS_ORIGINS=https://xxx.vercel.app,https://www.example.com
    # 注意：用 str 而非 list[str]，避免 pydantic-settings 把环境变量按 JSON 解析。
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
