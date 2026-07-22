from __future__ import annotations

import json
import logging
from typing import Any

from app.modules.llm.base import (
    OCR_PROMPT,
    answer_template_for,
    extract_template_for,
    template_for,
)

logger = logging.getLogger(__name__)


def _loads_json_block(text: str) -> Any:
    """从模型输出中健壮地解析 JSON（容忍 ```json 代码块与前后噪声）。"""
    s = text.strip()
    if s.startswith("```"):
        # 去掉围栏 ```json ... ```
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
        if s.startswith("json"):
            s = s[4:].strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # 退而求其次：截取第一个 [..] 或 {..}
        for open_ch, close_ch in (("[", "]"), ("{", "}")):
            start = s.find(open_ch)
            end = s.rfind(close_ch)
            if start != -1 and end > start:
                try:
                    return json.loads(s[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise


class OpenAICompatClient:
    """通用 OpenAI 兼容 chat/completions 客户端。

    适配任意 OpenAI 兼容厂商（豆包 / 智谱 GLM / 硅基流动 / 通义百炼 / DeepSeek 等），
    只需换 ``base_url`` / ``model`` / ``api_key``。网络调用失败时抛出，由上层处理
    （投稿保持 processing/失败态，可重试）。
    """

    def __init__(self, api_key: str, base_url: str, model: str, vision_model: str = "") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        # 多模态（图片 OCR）模型；留空则回退到主模型（多数纯文本模型不支持，会报错）。
        self.vision_model = vision_model or model

    async def _chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        import httpx  # 延迟导入：默认 mock 路径无需该依赖

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def format_content(self, raw: str, target_type: str) -> str:
        return await self._chat(template_for(target_type), raw)

    async def extract_items(self, raw: str, target_type: str) -> list[dict]:
        content = await self._chat(extract_template_for(target_type), raw, temperature=0.2)
        try:
            parsed = _loads_json_block(content)
        except json.JSONDecodeError:
            logger.warning("结构化解析 JSON 失败，回退整体作为单条：%s", content[:200])
            return _fallback_items(raw, target_type)
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return [p for p in parsed if isinstance(p, dict)]
        return _fallback_items(raw, target_type)

    async def complete_answer(self, question: str, target_type: str, context: str = "") -> str:
        user = question if not context else f"背景：\n{context}\n\n问题：\n{question}"
        return await self._chat(answer_template_for(target_type), user, temperature=0.4)

    async def ocr_image(self, data: bytes, content_type: str) -> str:
        """多模态模型 OCR：抽取图片中的文字为纯文本。"""
        import base64

        import httpx  # 延迟导入

        b64 = base64.b64encode(data).decode("ascii")
        data_url = f"data:{content_type or 'image/png'};base64,{b64}"
        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            body = resp.json()
        return (body["choices"][0]["message"]["content"] or "").strip()


def _fallback_items(raw: str, target_type: str) -> list[dict]:
    """解析失败时的兜底：至少返回一条，避免前端拿到空结果。"""
    title = (raw.strip().splitlines() or ["未命名"])[0][:60]
    if target_type == "sql":
        return [{"title": title, "prompt_md": raw, "answer_md": "", "difficulty": "medium"}]
    if target_type == "interview":
        return [
            {
                "company_name": "",
                "interview_type": "campus",
                "qa_items": [{"section": "round1", "question": raw[:200], "answer": ""}],
            }
        ]
    if target_type == "project":
        return [{"title": title, "description_md": raw, "implementation_md": ""}]
    return [{"title": title, "content_md": raw}]


# 向后兼容：旧名保留为别名。
DoubaoClient = OpenAICompatClient
