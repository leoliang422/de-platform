from __future__ import annotations

from app.modules.llm.base import template_for


class DoubaoClient:
    """豆包（火山方舟 Ark，OpenAI 兼容 chat/completions）。

    仅在 ``LLM_PROVIDER=doubao`` 且配置了 API key 时启用；网络调用失败时抛出，
    由上层处理（投稿保持 processing/失败态，可重试）。
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def format_content(self, raw: str, target_type: str) -> str:
        import httpx  # 延迟导入：默认 mock 路径无需该依赖

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": template_for(target_type)},
                {"role": "user", "content": raw},
            ],
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]
