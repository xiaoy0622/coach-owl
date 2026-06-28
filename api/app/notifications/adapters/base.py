"""Adapter interface + send result (channel-agnostic).

A :class:`NotificationAdapter` is the seam that keeps business logic ignorant of
the channel: it receives a fully-formed outbox row and reports whether the send
succeeded. :class:`EmailAdapter` is the email-channel interface; concrete impls
are :class:`~app.notifications.adapters.console.ConsoleEmailAdapter` now and
Resend/SES later. A future SMS/push channel is simply another
``NotificationAdapter`` subclass.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from app.models.enums import NotificationChannel
from app.models.notifications import Notification


@dataclass(frozen=True)
class SendResult:
    """Outcome of an adapter send. ``error`` is set only when ``ok`` is False."""

    ok: bool
    error: str | None = None

    @classmethod
    def success(cls) -> SendResult:
        return cls(ok=True)

    @classmethod
    def failure(cls, error: str) -> SendResult:
        return cls(ok=False, error=error)


class NotificationAdapter(ABC):
    """Sends one outbox row over a single channel.

    Implementations MUST be side-effect-idempotent enough that the outbox
    processor can safely retry a row that never reached ``sent`` — they must not
    assume they are called exactly once.
    """

    channel: ClassVar[NotificationChannel]

    @abstractmethod
    def send(self, notification: Notification) -> SendResult:
        """Deliver ``notification``; return success/failure (never raise for a
        normal delivery failure — return ``SendResult.failure`` instead)."""
        raise NotImplementedError


class EmailAdapter(NotificationAdapter):
    """Email-channel adapter interface (Console now; Resend/SES later)."""

    channel = NotificationChannel.email
