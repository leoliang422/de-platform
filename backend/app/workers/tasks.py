from __future__ import annotations

from typing import Any

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.core.database import SessionLocal
from app.modules.submissions.service import SubmissionService


async def process_submission(ctx: dict[str, Any], submission_id: int) -> None:
    """ARQ 任务：对投稿做大模型加工，完成后进入待审核状态。

    复用 ``SubmissionService.process``（与同步路径同一套逻辑）：仅处理 processing 态、
    幂等、失败落 ``failed`` 态并记录原因，便于用户/管理员重试。
    """
    async with SessionLocal() as db:
        await SubmissionService(db).process(submission_id)
