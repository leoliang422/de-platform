"""投稿文件解析：把上传的本地文件转成可插入投稿正文的 Markdown 片段。

分层：
- 文本类（txt/md/csv/json）直接解码，无需外部依赖（真实可用）。
- 图片直接以 Markdown 图片语法内联，前端即可展示（真实可用）。
- Word / PDF 等文档需要解析，交给「解析器」抽象：
    - ``MockExtractor``（默认）：仅返回占位说明 + 文件下载链接，不做真正解析。
    - ``LLMExtractor``：接入大模型 / 文档解析服务的骨架（占位）；未接入时工厂回退 mock，
      因此不影响现有功能。真实实现见方法内 TODO。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.config import get_settings

# content_type -> 扩展名。分三类，决定不同的处理路径。
TEXT_TYPES: dict[str, str] = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/x-markdown": ".md",
    "text/csv": ".csv",
    "application/json": ".json",
}
IMAGE_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
DOCUMENT_TYPES: dict[str, str] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/pdf": ".pdf",
}
ALLOWED_TYPES: dict[str, str] = {**TEXT_TYPES, **IMAGE_TYPES, **DOCUMENT_TYPES}


class ExtractorNotConfigured(RuntimeError):
    """真实解析服务未接入时抛出，工厂据此回退 mock。"""


@runtime_checkable
class DocumentExtractor(Protocol):
    name: str

    async def extract(
        self, *, data: bytes, filename: str, content_type: str, url: str | None
    ) -> str:
        """把文档二进制解析为 Markdown 文本。"""
        ...


class MockExtractor:
    """占位解析器：不解析文档内容，仅返回提示 + 下载链接，引导用户手动补充。"""

    name = "mock"

    async def extract(
        self, *, data: bytes, filename: str, content_type: str, url: str | None
    ) -> str:
        link = f"[{filename}]({url})" if url else filename
        return (
            f"> 已上传文件：{link}\n>\n"
            "> 文档解析 / 大模型识别尚未接入（占位）。请在下方手动补充或粘贴正文。\n"
        )


class LLMExtractor:
    """接入大模型 / 文档解析服务的骨架（占位）。

    真实实现思路：
    - Word/PDF：用解析库（python-docx / pdfplumber）或云文档服务转纯文本；
    - 图片：走多模态 OCR（如豆包 vision）识别文字；
    - 统一再交给 LLM 归一为规范 Markdown。
    凭证 / 服务未接入时 ``is_configured`` 返回 False，工厂不会选中它（回退 mock）。
    """

    name = "llm"

    @staticmethod
    def is_configured() -> bool:
        # TODO(M-real): 接入文档解析 / 多模态服务后返回真实判断。
        return False

    async def extract(
        self, *, data: bytes, filename: str, content_type: str, url: str | None
    ) -> str:
        # TODO(M-real): 解析文档 → 文本 → LLM 归一为 Markdown。
        raise ExtractorNotConfigured("文档 / 大模型解析尚未接入（占位）。")


def get_extractor() -> DocumentExtractor:
    if get_settings().file_extract_provider == "llm" and LLMExtractor.is_configured():
        return LLMExtractor()
    return MockExtractor()
