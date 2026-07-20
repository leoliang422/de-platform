"""M5-5B 异步队列：入队分支、入队失败回退、加工失败落态、重试。

同步加工的主流程仍由 tests/test_submissions.py 覆盖。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.catalog.models import Category
from app.modules.submissions.models import Submission
from app.modules.submissions.service import SubmissionService
from app.modules.users.models import User


async def _make_category(db: AsyncSession) -> int:
    cat = Category(section="knowledge", name="Hive", slug="hive", order=0)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat.id


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _user(db: AsyncSession, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one()


class _BoomLLM:
    async def format_content(self, raw: str, target_type: str) -> str:
        raise RuntimeError("模型开小差了")


async def _make_processing_submission(db: AsyncSession, user_id: int) -> Submission:
    submission = Submission(
        user_id=user_id,
        target_type="knowledge",
        title="待加工",
        raw_content="原始内容",
        extra={},
        status="processing",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


async def test_enqueue_path_returns_processing(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    async def fake_enqueue(self: SubmissionService, submission_id: int) -> None:
        calls.append(submission_id)

    monkeypatch.setattr(SubmissionService, "_enqueue", fake_enqueue)
    monkeypatch.setenv("TASK_QUEUE_ENABLED", "true")
    get_settings.cache_clear()
    try:
        token = await _register_and_login(client, "async1@test.io")
        cat_id = await _make_category(db)
        resp = await client.post(
            "/submissions",
            headers=_auth(token),
            json={
                "target_type": "knowledge",
                "title": "T",
                "raw_content": "hello",
                "category_id": cat_id,
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "processing"  # 异步：加工交给 Worker
        assert len(calls) == 1
    finally:
        get_settings.cache_clear()


async def test_enqueue_failure_falls_back_to_sync(
    client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom_enqueue(self: SubmissionService, submission_id: int) -> None:
        raise ConnectionError("redis 挂了")

    monkeypatch.setattr(SubmissionService, "_enqueue", boom_enqueue)
    monkeypatch.setenv("TASK_QUEUE_ENABLED", "true")
    get_settings.cache_clear()
    try:
        token = await _register_and_login(client, "async2@test.io")
        cat_id = await _make_category(db)
        resp = await client.post(
            "/submissions",
            headers=_auth(token),
            json={
                "target_type": "knowledge",
                "title": "T",
                "raw_content": "hello",
                "category_id": cat_id,
            },
        )
        assert resp.status_code == 201, resp.text
        # 入队失败自动回退同步加工（在后台任务内完成），投稿不会卡在 processing。
        sub_id = resp.json()["id"]
        mine = (await client.get("/submissions/me", headers=_auth(token))).json()
        assert next(s for s in mine if s["id"] == sub_id)["status"] == "pending_review"
    finally:
        get_settings.cache_clear()


async def test_process_is_idempotent(db: AsyncSession) -> None:
    user = User(email="proc@test.io", password_hash="x", nickname="p")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    submission = await _make_processing_submission(db, user.id)
    result = await SubmissionService(db).process(submission.id)
    assert result is not None
    assert result.status == "pending_review"
    assert result.processed_md

    # 再次处理已完成的投稿应无副作用（非 processing 态直接返回）。
    again = await SubmissionService(db).process(submission.id)
    assert again is not None
    assert again.status == "pending_review"


async def test_process_failure_sets_failed(db: AsyncSession) -> None:
    user = User(email="fail@test.io", password_hash="x", nickname="f")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    submission = await _make_processing_submission(db, user.id)
    result = await SubmissionService(db, llm=_BoomLLM()).process(submission.id)
    assert result is not None
    assert result.status == "failed"
    assert result.reject_reason and "加工失败" in result.reject_reason


async def test_retry_failed_submission(client: AsyncClient, db: AsyncSession) -> None:
    token = await _register_and_login(client, "retry@test.io")
    user = await _user(db, "retry@test.io")

    submission = await _make_processing_submission(db, user.id)
    await SubmissionService(db, llm=_BoomLLM()).process(submission.id)
    assert (await db.get(Submission, submission.id)).status == "failed"  # type: ignore[union-attr]

    resp = await client.post(f"/submissions/{submission.id}/retry", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    # 默认队列关闭 → 重试走同步加工成功。
    assert resp.json()["status"] == "pending_review"


async def test_retry_rejects_non_failed(client: AsyncClient, db: AsyncSession) -> None:
    token = await _register_and_login(client, "retry2@test.io")
    user = await _user(db, "retry2@test.io")
    submission = await _make_processing_submission(db, user.id)  # processing, 非 failed

    resp = await client.post(f"/submissions/{submission.id}/retry", headers=_auth(token))
    assert resp.status_code == 409


async def test_retry_forbidden_for_others(client: AsyncClient, db: AsyncSession) -> None:
    owner_token = await _register_and_login(client, "owner@test.io")
    _ = owner_token
    owner = await _user(db, "owner@test.io")
    submission = await _make_processing_submission(db, owner.id)
    await SubmissionService(db, llm=_BoomLLM()).process(submission.id)

    other_token = await _register_and_login(client, "intruder@test.io")
    resp = await client.post(f"/submissions/{submission.id}/retry", headers=_auth(other_token))
    assert resp.status_code == 403
