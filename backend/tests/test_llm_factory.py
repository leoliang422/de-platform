"""大模型工厂：通用 LLM_* 配置、旧 DOUBAO_* 兼容、无 key 回退 mock。"""

import pytest

from app.core.config import get_settings
from app.modules.llm.doubao import OpenAICompatClient
from app.modules.llm.factory import get_llm_client
from app.modules.llm.mock import MockLLM


def _reset() -> None:
    get_settings.cache_clear()


def test_default_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset()
    assert isinstance(get_llm_client(), MockLLM)
    _reset()


def test_non_mock_without_key_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "zhipu")
    _reset()
    try:
        assert isinstance(get_llm_client(), MockLLM)  # 无 key → 回退 mock
    finally:
        _reset()


def test_generic_llm_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "zhipu")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    monkeypatch.setenv("LLM_MODEL", "glm-4-flash")
    _reset()
    try:
        client = get_llm_client()
        assert isinstance(client, OpenAICompatClient)
        assert client.model == "glm-4-flash"
        assert client.base_url == "https://open.bigmodel.cn/api/paas/v4"
    finally:
        _reset()


def test_legacy_doubao_config_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "doubao")
    monkeypatch.setenv("DOUBAO_API_KEY", "legacy-key")
    _reset()
    try:
        client = get_llm_client()
        assert isinstance(client, OpenAICompatClient)  # 回退到 DOUBAO_* 变量
    finally:
        _reset()
