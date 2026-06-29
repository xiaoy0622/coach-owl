"""LLM client (CO-A01): offline-by-default, one place for the Anthropic call.

Every test runs with NO network. The HTTP layer (``httpx.post``) is monkeypatched
so we assert behaviour without ever leaving the process.
"""
from __future__ import annotations

import json

import pytest

from app.ai import llm


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self._status = status

    def raise_for_status(self) -> None:
        if self._status >= 400:
            raise RuntimeError(f"HTTP {self._status}")

    def json(self) -> dict:
        return self._payload


def _anthropic_payload(text: str) -> dict:
    return {
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 11, "output_tokens": 7},
    }


def _stub_httpx(monkeypatch, response: _FakeResponse, captured: dict | None = None):
    import httpx

    def _fake_post(url, **kwargs):  # noqa: ANN001
        if captured is not None:
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            captured["headers"] = kwargs.get("headers")
        return response

    monkeypatch.setattr(httpx, "post", _fake_post)


def test_unavailable_without_key(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", None)
    assert llm.is_available() is False
    with pytest.raises(llm.LLMUnavailableError):
        llm.complete("hello")


def test_complete_returns_text_and_uses_settings(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(llm.settings, "anthropic_model", "claude-sonnet-4-6")
    captured: dict = {}
    _stub_httpx(monkeypatch, _FakeResponse(_anthropic_payload("hi there")), captured)

    assert llm.is_available() is True
    out = llm.complete("ping", system="be terse", max_tokens=42)
    assert out == "hi there"
    # The request used configured model + key, and forwarded the system prompt.
    assert captured["json"]["model"] == "claude-sonnet-4-6"
    assert captured["json"]["max_tokens"] == 42
    assert captured["json"]["system"] == "be terse"
    assert captured["headers"]["x-api-key"] == "test-key"


def test_complete_wraps_transport_errors(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-key")
    import httpx

    def _boom(url, **kwargs):  # noqa: ANN001
        raise RuntimeError("connection refused")

    monkeypatch.setattr(httpx, "post", _boom)
    with pytest.raises(llm.LLMUnavailableError):
        llm.complete("ping")


def test_complete_rejects_empty_reply(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-key")
    _stub_httpx(monkeypatch, _FakeResponse(_anthropic_payload("   ")))
    with pytest.raises(llm.LLMUnavailableError):
        llm.complete("ping")


def test_structured_complete_parses_json_object(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-key")
    reply = "Here you go: " + json.dumps({"a": 1, "b": [2, 3]}) + " done"
    _stub_httpx(monkeypatch, _FakeResponse(_anthropic_payload(reply)))
    out = llm.structured_complete("x")
    assert out == {"a": 1, "b": [2, 3]}


def test_structured_complete_parses_json_array(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-key")
    reply = "```json\n[{\"name\": \"Ada\"}]\n```"
    _stub_httpx(monkeypatch, _FakeResponse(_anthropic_payload(reply)))
    out = llm.structured_complete("x")
    assert out == [{"name": "Ada"}]


def test_structured_complete_raises_on_non_json(monkeypatch):
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-key")
    _stub_httpx(monkeypatch, _FakeResponse(_anthropic_payload("no json here")))
    with pytest.raises(llm.LLMUnavailableError):
        llm.structured_complete("x")
