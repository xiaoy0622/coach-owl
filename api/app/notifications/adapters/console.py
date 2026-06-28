"""Console email adapter — "sends" by logging (no network, no API keys).

This is the MVP email channel: it records the message to the application log and
reports success, so the whole notification pipeline (dispatch -> outbox ->
process -> status=sent) is exercisable end-to-end without any email provider. A
real Resend/SES adapter implements the same :class:`EmailAdapter` interface and
swaps in via the registry with no business-logic change.
"""
from __future__ import annotations

import logging

from app.models.notifications import Notification
from app.notifications.adapters.base import EmailAdapter, SendResult

logger = logging.getLogger("coachowl.notifications.email")


class ConsoleEmailAdapter(EmailAdapter):
    """Logs the email instead of sending it; always succeeds."""

    def send(self, notification: Notification) -> SendResult:
        logger.info(
            "[email:console] to=%s template=%s dedupe=%s payload=%s",
            notification.recipient,
            notification.template,
            notification.dedupe_key,
            notification.payload,
        )
        return SendResult.success()
