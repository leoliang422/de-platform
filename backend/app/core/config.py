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

    # 前端站点根地址，用于拼接邮件里的重置/验证链接。
    frontend_base_url: str = "http://localhost:3000"

    # ---- 邮件发送 ----
    # mock：不真正发信，仅记录日志（本地/演示默认，找回密码返回 dev token 便于自测）。
    # smtp：真实 SMTP；凭证未配齐时自动回退 mock。获取方式见 docs/deployment.md「邮件发送」。
    email_provider: str = "mock"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # mock（默认，无需外部依赖）| 任意非 mock 值（如 zhipu/doubao/siliconflow）启用真实大模型。
    llm_provider: str = "mock"

    # ---- 通用 OpenAI 兼容大模型（推荐；智谱 GLM / 硅基流动 / 通义百炼 / DeepSeek 等）----
    # 把 LLM_PROVIDER 设为非 mock，并填以下三项即可；留空时回退旧的 DOUBAO_* 或 mock。
    # 获取方式（以免费的智谱 glm-4-flash 为例）见 docs/deployment.md「大模型接入」。
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    # 多模态模型（图片 OCR 抽字，用于面经/投稿一键解析图片）。留空则回退主模型。
    # 智谱有免费的 glm-4v-flash 可用；获取方式见 docs/deployment.md「大模型接入」。
    llm_vision_model: str = ""
    # 支付通道：mock（默认，同步结算）| wechat | alipay。
    # 选 wechat/alipay 但凭证未配齐时，工厂会自动回退到 mock（见 payment/provider.py）。
    payment_provider: str = "mock"

    # ---- 积分化访问控制（SQL / 面经 模块级）----
    # 每个模块（sql / interview）每个用户可免费查看的条目数，超出后需一次性用积分解锁整个模块。
    free_module_quota: int = 10
    # 一次性解锁整个 SQL / 面经 模块所需积分（可按运营调整）。
    sql_module_unlock_points: int = 50
    interview_module_unlock_points: int = 50

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

    # ---- 文件/图片存储 ----
    # local：存本地磁盘并由后端 /uploads 提供（默认，零外部依赖；Render 磁盘临时）。
    # s3  ：S3 兼容对象存储（R2/TOS/MinIO）；凭证未配齐时自动回退 local。
    storage_provider: str = "local"
    storage_local_dir: str = "uploads"
    # 投稿文件解析：local（默认，python-docx/pdfplumber 本地抽取 Word/PDF 文字，不依赖大模型）
    # | llm（本地抽取后再交大模型归一，未接入时自动回退 local）。见 docs/deployment.md。
    file_extract_provider: str = "local"
    # 公开访问前缀（留空则用请求自身的 base_url 拼接，本地/单域名部署即可）。
    storage_public_base_url: str = ""
    # S3 兼容占位配置；获取方式见 docs/deployment.md「文件存储」。
    s3_endpoint_url: str = ""
    s3_region: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_public_base_url: str = ""

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
