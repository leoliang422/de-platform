"""批量解析 + 答案补全（默认 MockLLM，无需真实大模型）。"""

from httpx import AsyncClient


async def _token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_parse_knowledge_text_multiple_items(client: AsyncClient) -> None:
    token = await _token(client, "parse1@test.io")
    resp = await client.post(
        "/submissions/parse",
        headers=_auth(token),
        data={"target_type": "knowledge", "text": "数据倾斜是什么\n\nSpark 宽依赖窄依赖"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["target_type"] == "knowledge"
    assert len(body["items"]) == 2
    assert body["items"][0]["title"]
    assert "content_md" in body["items"][0]


async def test_parse_sql_shape(client: AsyncClient) -> None:
    token = await _token(client, "parse2@test.io")
    resp = await client.post(
        "/submissions/parse",
        headers=_auth(token),
        data={"target_type": "sql", "text": "连续登录三天的用户"},
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert {"title", "prompt_md", "answer_md", "difficulty"} <= item.keys()


async def test_parse_interview_shape(client: AsyncClient) -> None:
    token = await _token(client, "parse3@test.io")
    resp = await client.post(
        "/submissions/parse",
        headers=_auth(token),
        data={"target_type": "interview", "text": "问了数据倾斜\n\n问了数仓分层"},
    )
    assert resp.status_code == 200, resp.text
    post = resp.json()["items"][0]
    assert "qa_items" in post and len(post["qa_items"]) == 2


async def test_parse_image_uses_ocr(client: AsyncClient) -> None:
    """图片走多模态 OCR（MockLLM 返回占位文本），再交结构化拆分。"""
    token = await _token(client, "parseimg@test.io")
    # 1x1 PNG 的最小字节即可，MockLLM.ocr_image 不真正解析像素。
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    resp = await client.post(
        "/submissions/parse",
        headers=_auth(token),
        data={"target_type": "knowledge"},
        files={"file": ("shot.png", png, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"], "OCR 文本应被拆分为至少一条草稿"


async def test_parse_requires_content(client: AsyncClient) -> None:
    token = await _token(client, "parse4@test.io")
    resp = await client.post(
        "/submissions/parse", headers=_auth(token), data={"target_type": "knowledge"}
    )
    assert resp.status_code == 422


async def test_parse_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/submissions/parse", data={"target_type": "knowledge", "text": "x"})
    assert resp.status_code in (401, 403)


async def test_complete_answer(client: AsyncClient) -> None:
    token = await _token(client, "ans1@test.io")
    resp = await client.post(
        "/submissions/complete-answer",
        headers=_auth(token),
        json={"target_type": "sql", "question": "如何求连续登录三天的用户？"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["answer"]
