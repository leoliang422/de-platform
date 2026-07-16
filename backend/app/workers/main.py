from __future__ import annotations

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import process_submission


class WorkerSettings:
    """ARQ Worker 入口：`arq app.workers.main.WorkerSettings`。"""

    functions = [process_submission]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
