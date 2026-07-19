from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.interview import service as interview_service
from app.modules.knowledge import service as knowledge_service
from app.modules.llm.base import LLMClient
from app.modules.llm.factory import get_llm_client
from app.modules.notifications.service import NotificationService
from app.modules.points.service import POINTS_BY_TYPE, PointsService
from app.modules.projects import service as project_service
from app.modules.sql_bank import service as sql_service
from app.modules.submissions.models import Submission
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import SubmissionCreate
from app.modules.users.models import User

logger = logging.getLogger(__name__)


def _extra_from(data: SubmissionCreate) -> dict[str, Any]:
    # Decimal 不可 JSON 序列化，价格以字符串入库。
    return {
        "category_id": data.category_id,
        "is_paid": data.is_paid,
        "price_cash": str(data.price_cash) if data.price_cash is not None else None,
        "price_points": data.price_points,
        "prompt_md": data.prompt_md,
        "difficulty": data.difficulty,
        "tags": data.tags,
        "company_name": data.company_name,
        "interview_type": data.interview_type,
        "qa_items": [q.model_dump() for q in data.qa_items] if data.qa_items else None,
        "level": data.level,
        "access_type": data.access_type,
        "implementation_md": data.implementation_md,
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


class SubmissionService:
    def __init__(self, db: AsyncSession, llm: LLMClient | None = None) -> None:
        self.db = db
        self.repo = SubmissionRepository(db)
        self.llm = llm or get_llm_client()

    async def create(self, user_id: int, data: SubmissionCreate) -> Submission:
        self._validate(data)
        submission = Submission(
            user_id=user_id,
            target_type=data.target_type,
            title=data.title,
            raw_content=data.raw_content,
            extra=_extra_from(data),
            status="processing",
        )
        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)

        await self._dispatch(submission.id)
        await self.db.refresh(submission)
        return submission

    def _validate(self, data: SubmissionCreate) -> None:
        if data.target_type == "interview":
            _require(bool(data.company_name), "面经投稿需填写企业名称")
            _require(bool(data.interview_type), "面经投稿需选择类型")
            has_qa = any((q.question.strip() or q.answer.strip()) for q in (data.qa_items or []))
            _require(has_qa, "面经投稿需至少填写一条问答")
            return
        # 非面经：需标题与正文
        _require(bool(data.title.strip()), "投稿需填写标题")
        _require(bool(data.raw_content.strip()), "投稿需填写正文")
        if data.target_type == "knowledge":
            _require(data.category_id is not None, "八股投稿需选择所属文件夹")
        if data.target_type == "sql":
            _require(bool(data.prompt_md), "SQL 投稿需填写题目")

    async def _dispatch(self, submission_id: int) -> None:
        """按配置把加工投递到异步队列；队列不可用时安全回退到同步加工。"""
        if get_settings().task_queue_enabled:
            try:
                await self._enqueue(submission_id)
                return
            except Exception as exc:  # noqa: BLE001 - 队列故障不应阻断投稿
                logger.warning(
                    "投稿 %s 入队失败，回退同步加工：%s", submission_id, exc, exc_info=True
                )
        await self.process(submission_id)

    async def _enqueue(self, submission_id: int) -> None:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
        try:
            await pool.enqueue_job("process_submission", submission_id)
        finally:
            await pool.aclose()

    async def process(self, submission_id: int) -> Submission | None:
        """对投稿做大模型加工（同步路径与 Worker 共用）。

        - 仅处理 ``processing`` 态，天然幂等（重复投递不会二次加工）。
        - 加工异常落 ``failed`` 态并记录原因，供用户/管理员重试。
        """
        submission = await self.repo.get(submission_id)
        if submission is None or submission.status != "processing":
            return submission
        try:
            submission.processed_md = await self.llm.format_content(
                submission.raw_content, submission.target_type
            )
            submission.status = "pending_review"
            submission.reject_reason = None
        except Exception as exc:  # noqa: BLE001 - 记录失败原因，避免卡在 processing
            logger.exception("投稿 %s 加工失败", submission_id)
            submission.status = "failed"
            submission.reject_reason = f"加工失败：{exc}"[:500]
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def retry(self, submission_id: int, user: User) -> Submission:
        """重试加工失败的投稿（作者本人或管理员）。"""
        submission = await self.repo.get(submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投稿不存在")
        if user.role != "admin" and submission.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该投稿")
        if submission.status != "failed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"当前状态为 {submission.status}，仅失败的投稿可重试",
            )
        submission.status = "processing"
        submission.reject_reason = None
        await self.db.commit()
        await self._dispatch(submission_id)
        await self.db.refresh(submission)
        return submission

    async def approve(self, submission_id: int, content: str | None = None) -> Submission:
        submission = await self.repo.get(submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投稿不存在")
        if submission.status != "pending_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"当前状态为 {submission.status}，无法审核发布",
            )

        # 管理员可覆盖最终发布正文（原文 / AI 稿 / 手动编辑），置入 processed_md 后统一发布。
        if content is not None and content.strip():
            submission.processed_md = content

        ref_id = await self._publish(submission)
        submission.published_ref_id = ref_id
        submission.status = "published"

        await PointsService(self.db).grant(
            user_id=submission.user_id,
            delta=POINTS_BY_TYPE[submission.target_type],
            reason=f"投稿发布：{submission.target_type}",
            ref_type="submission",
            ref_id=submission.id,
        )
        label = submission.title or (submission.extra or {}).get("company_name") or "你的投稿"
        await NotificationService(self.db).notify(
            user_id=submission.user_id,
            type="submission_approved",
            title="投稿已发布",
            body=f"你的投稿《{label}》已通过审核并发布。",
            link="/submit",
        )
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def reject(self, submission_id: int, reason: str) -> Submission:
        submission = await self.repo.get(submission_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投稿不存在")
        if submission.status != "pending_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"当前状态为 {submission.status}，无法驳回",
            )
        submission.status = "rejected"
        submission.reject_reason = reason
        label = submission.title or (submission.extra or {}).get("company_name") or "你的投稿"
        await NotificationService(self.db).notify(
            user_id=submission.user_id,
            type="submission_rejected",
            title="投稿被驳回",
            body=f"你的投稿《{label}》未通过审核：{reason}",
            link="/submit",
        )
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def _publish(self, submission: Submission) -> int:
        extra = submission.extra or {}
        body = submission.processed_md or submission.raw_content
        author_id = submission.user_id
        price_cash = Decimal(extra["price_cash"]) if extra.get("price_cash") is not None else None

        if submission.target_type == "knowledge":
            item = await knowledge_service.create_published(
                self.db,
                title=submission.title,
                content_md=body,
                category_id=extra.get("category_id"),
                is_paid=bool(extra.get("is_paid")),
                price_cash=price_cash,
                price_points=extra.get("price_points"),
                author_id=author_id,
            )
            return item.id

        if submission.target_type == "sql":
            question = await sql_service.create_published(
                self.db,
                title=submission.title,
                prompt_md=extra.get("prompt_md") or "",
                answer_md=body,
                difficulty=extra.get("difficulty") or "medium",
                tags=extra.get("tags") or "",
                category_id=extra.get("category_id"),
                author_id=author_id,
            )
            return question.id

        if submission.target_type == "interview":
            company_name = extra.get("company_name") or "未知企业"
            post = await interview_service.create_published(
                self.db,
                company_name=company_name,
                # 面经已去掉标题与整体感受：内部标题用企业名，正文置空。
                title=company_name,
                content_md="",
                interview_type=extra.get("interview_type"),
                qa_items=extra.get("qa_items"),
                author_id=author_id,
            )
            return post.id

        project = await project_service.create_published(
            self.db,
            title=submission.title,
            description_md=body,
            implementation_md=extra.get("implementation_md") or "",
            level=extra.get("level") or "basic",
            access_type=extra.get("access_type") or "free",
            price_cash=price_cash,
            price_points=extra.get("price_points"),
            author_id=author_id,
        )
        return project.id
