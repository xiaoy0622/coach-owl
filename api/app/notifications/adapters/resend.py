"""Resend email adapter (CO-N02): real email send over the Resend REST API.

Implements the same :class:`EmailAdapter` seam as the console adapter, so the
registry swaps it in by config (``email_provider=resend``) with zero
business-logic change. Like the AI client (app/ai/llm.py) it reuses the
already-installed ``httpx`` for a single POST rather than pulling the official
``resend`` SDK — the dependency surface stays small and the call is one request.

Contract (matches :class:`NotificationAdapter`):

* Never raises on a normal delivery failure. A missing key, non-2xx response,
  timeout, or transport error all return :meth:`SendResult.failure` so the outbox
  processor records ``failed`` and a later run can retry — the worker never dies.
* Retry-safe: ``send`` has no local mutable state, so the processor may re-call a
  row that never reached ``sent``. (A provider-side idempotency key could be
  added here later for at-most-once external sends.)

An :class:`SesEmailAdapter` would slot in beside this file the same way: subclass
:class:`EmailAdapter`, render via :mod:`app.notifications.templates`, POST to SES,
and register it in the registry under ``email_provider=ses``.
"""
from __future__ import annotations

import logging

from app.core.config import settings
from app.models.notifications import Notification
from app.notifications.adapters.base import EmailAdapter, SendResult
from app.notifications.templates import render

logger = logging.getLogger("coachowl.notifications.email")

_PROVIDER = "resend"


class ResendEmailAdapter(EmailAdapter):
    """Sends email via Resend's ``POST /emails`` endpoint using httpx."""

    def send(self, notification: Notification) -> SendResult:
        api_key = settings.resend_api_key
        if not api_key:
            # provider=resend but no key: degrade safely, do not crash the worker.
            logger.error(
                "[email:resend] send skipped to=%s template=%s status=no_api_key",
                notification.recipient,
                notification.template,
            )
            return SendResult.failure("resend: RESEND_API_KEY not configured")

        subject, html = render(notification)
        body = {
            "from": settings.email_from,
            "to": [notification.recipient],
            "subject": subject,
            "html": html,
        }
        url = f"{settings.resend_base_url.rstrip('/')}/emails"

        try:
            import httpx

            resp = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "content-type": "application/json",
                },
                json=body,
                timeout=settings.resend_timeout,
            )
        except Exception as exc:  # noqa: BLE001 - transport/timeout -> failure, not raise
            logger.warning(
                "[email:resend] to=%s template=%s status=transport_error err=%s",
                notification.recipient,
                notification.template,
                exc,
            )
            return SendResult.failure(f"resend: transport error: {exc}")

        if not 200 <= resp.status_code < 300:
            detail = (resp.text or "").strip()[:500]
            logger.warning(
                "[email:resend] to=%s template=%s status=http_%s detail=%s",
                notification.recipient,
                notification.template,
                resp.status_code,
                detail,
            )
            return SendResult.failure(
                f"resend: HTTP {resp.status_code}: {detail}"
            )

        logger.info(
            "[email:%s] to=%s template=%s status=sent http=%s",
            _PROVIDER,
            notification.recipient,
            notification.template,
            resp.status_code,
        )
        return SendResult.success()
