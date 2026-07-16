from __future__ import annotations

TYPE_LABEL: dict[str, str] = {
    "knowledge": "知识点",
    "sql": "SQL 解答",
    "interview": "面试经历",
    "project": "项目介绍",
}


class MockLLM:
    """无需外部依赖的确定性实现，保证本地/CI 可演示投稿加工流程。"""

    async def format_content(self, raw: str, target_type: str) -> str:
        label = TYPE_LABEL.get(target_type, "内容")
        body = raw.strip() or "（空）"
        return f"## {label}（AI 已整理）\n\n{body}\n"
