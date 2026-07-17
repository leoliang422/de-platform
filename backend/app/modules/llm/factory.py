from __future__ import annotations

from app.core.config import get_settings
from app.modules.llm.base import LLMClient
from app.modules.llm.doubao import OpenAICompatClient
from app.modules.llm.mock import MockLLM


def get_llm_client() -> LLMClient:
    """按配置返回大模型客户端。

    - ``LLM_PROVIDER=mock``（默认）→ MockLLM。
    - 其它值 → OpenAI 兼容客户端：优先用通用 ``LLM_*`` 配置，回退旧的 ``DOUBAO_*``；
      无 API key 时安全回退 MockLLM，因此未配置也不影响运行。
    """
    s = get_settings()
    if s.llm_provider == "mock":
        return MockLLM()
    api_key = s.llm_api_key or s.doubao_api_key
    if not api_key:
        return MockLLM()
    return OpenAICompatClient(
        api_key=api_key,
        base_url=s.llm_base_url or s.doubao_base_url,
        model=s.llm_model or s.doubao_model,
    )
