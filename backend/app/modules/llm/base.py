from __future__ import annotations

from typing import Protocol

# 各内容类型对应的整理模板提示，指导模型把原始文本规范为统一 Markdown。
TEMPLATES: dict[str, str] = {
    "knowledge": "你是数据开发领域的技术编辑。请把下面的知识点整理为结构清晰的中文 Markdown，"
    "使用二级标题、要点列表，保留代码块，不要杜撰内容。",
    "sql": "你是数据开发面试官。请把下面的 SQL 解答整理为规范中文 Markdown，"
    "包含思路说明与最终 SQL 代码块，不要杜撰内容。",
    "interview": "你是面经整理编辑。请把下面的面试经历整理为条理清晰的中文 Markdown，"
    "按面试轮次/问题组织，保留真实细节，不要杜撰。",
    "project": "你是数据开发项目导师。请把下面的项目描述整理为规范中文 Markdown，"
    "突出业务背景、技术方案与亮点，不要杜撰。",
}


def template_for(target_type: str) -> str:
    return TEMPLATES.get(target_type, TEMPLATES["knowledge"])


class LLMClient(Protocol):
    async def format_content(self, raw: str, target_type: str) -> str: ...
