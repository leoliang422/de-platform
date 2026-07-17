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

# 结构化拆分提示：从原始文本中抽出多条投稿草稿，只输出 JSON。
EXTRACT_TEMPLATES: dict[str, str] = {
    "knowledge": (
        "你是数据开发领域的技术编辑。请从用户提供的原始文本中提取其中涉及的多个知识点，"
        "每个知识点抽象为一条，包含简洁标题与规范的中文 Markdown 正文（保留代码块）。"
        '只输出 JSON 数组，格式：[{"title": "标题", "content_md": "正文Markdown"}]。'
        "不要杜撰内容，不要输出 JSON 以外的任何文字。"
    ),
    "sql": (
        "你是数据开发面试官。请从用户提供的原始文本中提取多道 SQL 题目，每题一条，包含标题、"
        "题干(prompt_md)、参考答案(answer_md，若原文没有答案则留空字符串)、"
        "难度(difficulty，取 easy/medium/hard)。只输出 JSON 数组，格式："
        '[{"title":"","prompt_md":"","answer_md":"","difficulty":"medium"}]。'
        "不要杜撰题目，不要输出 JSON 以外的任何文字。"
    ),
    "interview": (
        "你是面经整理编辑。请从用户提供的原始文本中提取一场面试的信息：企业名(company_name)、"
        "面试类型(interview_type，取 campus/social/daily/summer)、"
        "以及按轮次组织的问答列表(qa_items)，"
        "每条问答含 section(round1/round2/round3/hr)、question、"
        "answer(若原文没有答案则留空字符串)。"
        '只输出 JSON 对象，格式：{"company_name":"","interview_type":"campus",'
        '"qa_items":[{"section":"round1","question":"","answer":""}]}。'
        "不要杜撰内容，不要输出 JSON 以外的任何文字。"
    ),
    "project": (
        "你是数据开发项目导师。请从用户提供的原始文本中提取多个项目，每个一条，包含标题(title)、"
        "项目描述(description_md)、实现说明(implementation_md，可留空)。"
        '只输出 JSON 数组，格式：[{"title":"","description_md":"","implementation_md":""}]。'
        "不要杜撰内容，不要输出 JSON 以外的任何文字。"
    ),
}

# 答案补全提示：针对单个问题生成参考答案。
ANSWER_TEMPLATES: dict[str, str] = {
    "knowledge": "你是数据开发领域专家。请针对下面的问题给出准确、简洁的中文 Markdown 参考答案。",
    "sql": "你是数据开发面试官。请针对下面的 SQL 题目给出解题思路与 SQL 代码块（中文）。",
    "interview": "你是资深数据开发面试官。请针对下面的面试问题给出条理清晰的中文参考答案。",
    "project": "你是数据开发项目导师。请针对下面的项目相关问题给出专业的中文参考答案。",
}


def template_for(target_type: str) -> str:
    return TEMPLATES.get(target_type, TEMPLATES["knowledge"])


def extract_template_for(target_type: str) -> str:
    return EXTRACT_TEMPLATES.get(target_type, EXTRACT_TEMPLATES["knowledge"])


def answer_template_for(target_type: str) -> str:
    return ANSWER_TEMPLATES.get(target_type, ANSWER_TEMPLATES["knowledge"])


class LLMClient(Protocol):
    async def format_content(self, raw: str, target_type: str) -> str: ...

    async def extract_items(self, raw: str, target_type: str) -> list[dict]: ...

    async def complete_answer(self, question: str, target_type: str, context: str = "") -> str: ...
