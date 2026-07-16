from __future__ import annotations

from typing import Any

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.core.database import SessionLocal
from app.modules.llm.factory import get_llm_client
from app.modules.submissions.models import Submission


async def process_submission(ctx: dict[str, Any], submission_id: int) -> None:
    """ARQ 任务：对投稿做大模型加工，完成后进入待审核状态。"""
    llm = get_llm_client()
    async with SessionLocal() as db:
        submission = await db.get(Submission, submission_id)
        if submission is None:
            return
        submission.processed_md = await llm.format_content(
            submission.raw_content, submission.target_type
        )
        submission.status = "pending_review"
        await db.commit()
