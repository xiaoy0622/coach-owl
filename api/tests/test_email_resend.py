"""CO-N02: Resend email adapter, templates, and config-driven adapter selection.

Every test is fully offline: the success/failure paths monkeypatch ``httpx.post``
(no socket is ever opened) and no test requires a real ``RESEND_API_KEY``. Console
stays the default provider, so the rest of the suite is untouched.
"""
from __future__ import annotations

import uuid

import httpx
import pytest

from app.core.config import settings
from app.models.enums import NotificationChannel
from app.models.notifications import Notification
from app.notifications.adapters import (
    ConsoleEmailAdapter,
    ResendEmailAdapter,
    build_email_adapter,
)
from app.notifications.adapters.base import SendResult
from app.notifications.templates import KNOWN_TEMPLATES, render


def _note(template="lesson_reminder", payload=None) -> Notification:
    """A transient (un-persisted) outbox row — adapters/templates need no DB."""
    if payload is None:
        payload = {"startsAt": "2026-06-30T10:00:00+00:00"}
    return Notification(
        org_id=uuid.uuid4(),
        channel=NotificationChannel.email,
        template=template,
        recipient="sam@example.com",
        payload=payload,
        dedupe_key="k-" + uuid.uuid4().hex,
    )


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


# --------------------------------------------------------------------------- #
# (a) success path — httpx mocked, no network                                  #
# --------------------------------------------------------------------------- #
def test_resend_success(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    captured: dict = {}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse(200, '{"id":"abc"}')

    monkeypatch.setattr(httpx, "post", fake_post)

    result = ResendEmailAdapter().send(_note())

    assert result.ok is True
    assert result.error is None
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["to"] == ["sam@example.com"]
    assert captured["json"]["from"] == settings.email_from
    assert captured["json"]["subject"]
    assert captured["json"]["html"]


def test_resend_accepts_any_2xx(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse(202))
    assert ResendEmailAdapter().send(_note()).ok is True


# --------------------------------------------------------------------------- #
# (b) failure paths — non-2xx + transport error, never raise                   #
# --------------------------------------------------------------------------- #
def test_resend_non_2xx_returns_failure(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-key")
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _FakeResponse(422, "invalid")
    )

    result = ResendEmailAdapter().send(_note())

    assert result.ok is False
    assert "422" in result.error


def test_resend_transport_error_returns_failure(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-key")

    def boom(*a, **k):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", boom)

    result = ResendEmailAdapter().send(_note())  # must not raise

    assert result.ok is False
    assert result.error


def test_resend_missing_key_fails_safely(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", None)

    def fail_if_called(*a, **k):  # network must never be attempted
        raise AssertionError("httpx.post should not be called without a key")

    monkeypatch.setattr(httpx, "post", fail_if_called)

    result = ResendEmailAdapter().send(_note())

    assert isinstance(result, SendResult)
    assert result.ok is False
    assert result.error


# --------------------------------------------------------------------------- #
# (c) template rendering — non-empty subject + html for every known template   #
# --------------------------------------------------------------------------- #
_PAYLOADS = {
    "lesson_reminder": {
        "studentName": "Sam",
        "startsAt": "2026-06-30T10:00:00+00:00",
        "offset": "1h",
    },
    "low_balance": {"studentName": "Sam", "balance": 2, "threshold": 5},
    "lesson_cancelled": {"startsAt": "2026-06-30T10:00:00+00:00"},
    "lesson_rescheduled": {"startsAt": "2026-07-01T09:00:00+00:00"},
}


@pytest.mark.parametrize("template", KNOWN_TEMPLATES)
def test_template_renders_non_empty(template):
    subject, html = render(_note(template, _PAYLOADS[template]))
    assert subject.strip()
    assert html.strip()
    assert "<" in html  # produced HTML, not a bare string


def test_known_templates_cover_system_identifiers():
    # The four identifiers the codebase actually emits today.
    assert set(KNOWN_TEMPLATES) == {
        "lesson_reminder",
        "low_balance",
        "lesson_cancelled",
        "lesson_rescheduled",
    }


def test_render_unknown_template_falls_back_non_empty():
    subject, html = render(_note("brand_new_template", {}))
    assert subject.strip()
    assert html.strip()


def test_render_tolerates_missing_payload_keys():
    subject, html = render(_note("lesson_reminder", {}))
    assert subject.strip()
    assert html.strip()


# --------------------------------------------------------------------------- #
# (d) registry adapter selection by email_provider                            #
# --------------------------------------------------------------------------- #
def test_build_email_adapter_console():
    assert isinstance(build_email_adapter("console"), ConsoleEmailAdapter)


def test_build_email_adapter_resend():
    assert isinstance(build_email_adapter("resend"), ResendEmailAdapter)


def test_build_email_adapter_unknown_falls_back_to_console():
    assert isinstance(build_email_adapter("smoke-signals"), ConsoleEmailAdapter)


def test_build_email_adapter_defaults_to_settings(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "resend")
    assert isinstance(build_email_adapter(), ResendEmailAdapter)
    monkeypatch.setattr(settings, "email_provider", "console")
    assert isinstance(build_email_adapter(), ConsoleEmailAdapter)
