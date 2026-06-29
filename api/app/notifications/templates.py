"""Email message templates (CO-N02): render subject + HTML from a payload.

A network adapter (Resend/SES) needs an actual subject and body; the console
adapter never did. This module is the single place that turns a notification's
``template`` name + ``payload`` (the camelCase dict the dispatcher persisted) into
``(subject, html)``. It is deliberately dependency-free — plain f-strings, no
Jinja — so it carries no template-injection surface and no new dependency.

Template identifiers are the ones the system actually emits today:

* ``lesson_reminder``    — app/workers/reminders.py (payload: studentName,
  startsAt, offset)
* ``low_balance``        — app/notifications/hooks.py (payload: studentName,
  balance, threshold)
* ``lesson_cancelled``   — app/services/scheduling.py (payload: startsAt, ...)
* ``lesson_rescheduled`` — app/services/scheduling.py (payload: startsAt, ...)

Unknown templates fall back to a generic body so a send never produces an empty
subject/HTML (which some providers reject).
"""
from __future__ import annotations

import html
from collections.abc import Callable

from app.models.notifications import Notification

_PRODUCT = "CoachOwl"


def _esc(value: object) -> str:
    """HTML-escape a payload value (None -> empty string)."""
    return html.escape("" if value is None else str(value))


def _wrap(heading: str, body_html: str) -> str:
    """Minimal, inline-styled HTML document shared by every template."""
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;'
        'font-size:15px;color:#222;line-height:1.5">'
        f"<h2 style=\"margin:0 0 12px\">{heading}</h2>"
        f"{body_html}"
        '<hr style="border:none;border-top:1px solid #eee;margin:20px 0">'
        f'<p style="font-size:12px;color:#888">{_PRODUCT}</p>'
        "</div>"
    )


def _lesson_reminder(payload: dict) -> tuple[str, str]:
    name = payload.get("studentName") or "there"
    starts_at = payload.get("startsAt")
    subject = f"{_PRODUCT}: upcoming lesson reminder"
    body = _wrap(
        "Lesson reminder",
        f"<p>Hi {_esc(name)},</p>"
        f"<p>This is a reminder that you have a lesson scheduled for "
        f"<strong>{_esc(starts_at)}</strong>.</p>",
    )
    return subject, body


def _low_balance(payload: dict) -> tuple[str, str]:
    name = payload.get("studentName") or "there"
    balance = payload.get("balance")
    subject = f"{_PRODUCT}: your session balance is running low"
    body = _wrap(
        "Low session balance",
        f"<p>Hi {_esc(name)},</p>"
        f"<p>Your remaining session balance is "
        f"<strong>{_esc(balance)}</strong>. Top up to avoid interruption.</p>",
    )
    return subject, body


def _lesson_cancelled(payload: dict) -> tuple[str, str]:
    starts_at = payload.get("startsAt")
    subject = f"{_PRODUCT}: your lesson was cancelled"
    body = _wrap(
        "Lesson cancelled",
        f"<p>Your lesson scheduled for <strong>{_esc(starts_at)}</strong> "
        f"has been cancelled.</p>",
    )
    return subject, body


def _lesson_rescheduled(payload: dict) -> tuple[str, str]:
    starts_at = payload.get("startsAt")
    subject = f"{_PRODUCT}: your lesson was rescheduled"
    body = _wrap(
        "Lesson rescheduled",
        f"<p>Your lesson has been rescheduled to "
        f"<strong>{_esc(starts_at)}</strong>.</p>",
    )
    return subject, body


# Template name -> renderer. Adding a template is one entry here.
_TEMPLATES: dict[str, Callable[[dict], tuple[str, str]]] = {
    "lesson_reminder": _lesson_reminder,
    "low_balance": _low_balance,
    "lesson_cancelled": _lesson_cancelled,
    "lesson_rescheduled": _lesson_rescheduled,
}

# Templates this module knows how to render specifically (for tests/introspection).
KNOWN_TEMPLATES: tuple[str, ...] = tuple(_TEMPLATES)


def _generic(template: str, payload: dict) -> tuple[str, str]:
    subject = f"{_PRODUCT} notification"
    body = _wrap(
        "Notification",
        f"<p>You have a new {_esc(template)} notification.</p>",
    )
    return subject, body


def render(notification: Notification) -> tuple[str, str]:
    """Render ``notification`` to ``(subject, html)`` — both always non-empty.

    Falls back to a generic body for any template name without a dedicated
    renderer, so a real provider never receives an empty subject/HTML.
    """
    payload = notification.payload or {}
    renderer = _TEMPLATES.get(notification.template)
    if renderer is None:
        return _generic(notification.template, payload)
    return renderer(payload)
