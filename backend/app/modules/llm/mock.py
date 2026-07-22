from __future__ import annotations

TYPE_LABEL: dict[str, str] = {
    "knowledge": "知识点",
    "sql": "SQL 解答",
    "interview": "面试经历",
    "project": "项目介绍",
}


def _chunks(raw: str) -> list[str]:
    """按空行把原始文本切成若干段，供确定性拆分使用。"""
    parts = [p.strip() for p in raw.split("\n\n") if p.strip()]
    return parts or ([raw.strip()] if raw.strip() else [])


class MockLLM:
    """无需外部依赖的确定性实现，保证本地/CI 可演示投稿加工流程。"""

    async def format_content(self, raw: str, target_type: str) -> str:
        label = TYPE_LABEL.get(target_type, "内容")
        body = raw.strip() or "（空）"
        return f"## {label}（AI 已整理）\n\n{body}\n"

    async def extract_items(self, raw: str, target_type: str) -> list[dict]:
        chunks = _chunks(raw)
        if target_type == "sql":
            return [
                {
                    "title": c.splitlines()[0][:60],
                    "prompt_md": c,
                    "answer_md": "",
                    "difficulty": "medium",
                }
                for c in chunks
            ]
        if target_type == "interview":
            return [
                {
                    "company_name": "",
                    "interview_type": "campus",
                    "qa_items": [
                        {"section": "round1", "question": c.splitlines()[0][:200], "answer": ""}
                        for c in chunks
                    ],
                }
            ]
        if target_type == "project":
            return [
                {"title": c.splitlines()[0][:60], "description_md": c, "implementation_md": ""}
                for c in chunks
            ]
        # knowledge（默认）
        return [{"title": c.splitlines()[0][:60], "content_md": c} for c in chunks]

    async def complete_answer(self, question: str, target_type: str, context: str = "") -> str:
        label = TYPE_LABEL.get(target_type, "内容")
        return f"（AI 生成，待人工确认）针对「{question.strip()[:80]}」的{label}参考答案。"

    async def ocr_image(self, data: bytes, content_type: str) -> str:
        # mock：不做真实 OCR，返回占位提示（未配置多模态模型时的确定性行为）。
        ct = content_type or "image"
        return f"（图片 OCR 占位：未配置多模态大模型，{ct} 共 {len(data)} 字节）"
