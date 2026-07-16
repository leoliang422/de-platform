from __future__ import annotations

from app.core.config import get_settings
from app.modules.llm.base import LLMClient
from app.modules.llm.doubao import DoubaoClient
from app.modules.llm.mock import MockLLM


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "doubao" and settings.doubao_api_key:
        return DoubaoClient(
            api_key=settings.doubao_api_key,
            base_url=settings.doubao_base_url,
            model=settings.doubao_model,
        )
    return MockLLM()
