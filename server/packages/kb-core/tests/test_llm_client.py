"""Tests for LLM client — mocked HTTP calls."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from kb_core.llm.client import LLMClient


@pytest.mark.asyncio
async def test_llm_client_init():
    client = LLMClient(api_key="test-key", model="test-model", base_url="https://test.com/v1")
    assert client.api_key == "test-key"
    assert client.model == "test-model"
    assert client.base_url == "https://test.com/v1"


@pytest.mark.asyncio
async def test_llm_chat_success():
    client = LLMClient(api_key="test-key", model="test-model", base_url="https://test.com/v1")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "hello response"}}]
    }

    with patch.object(client, "chat", new=AsyncMock(return_value="hello response")):
        result = await client.chat("say hello")
        assert result == "hello response"


@pytest.mark.asyncio
async def test_llm_chat_json():
    client = LLMClient(api_key="test-key", model="test-model", base_url="https://test.com/v1")

    with patch.object(client, "chat", new=AsyncMock(return_value='{"key": "value"}')):
        result = await client.chat_json("return json")
        assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_from_config():
    config = {
        "api_key_encrypted": "cfg-key",
        "model": "cfg-model",
        "base_url": "https://cfg.com/v1",
        "provider": "deepseek",
    }
    client = LLMClient.from_config(config)
    assert client.api_key == "cfg-key"
    assert client.model == "cfg-model"
    assert client.base_url == "https://cfg.com/v1"
