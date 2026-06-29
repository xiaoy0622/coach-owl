"""Channel adapters (CO-N01/N02).

An adapter turns an outbox row into a real "send" for one channel. The dispatcher
and outbox processor only ever talk to the :class:`AdapterRegistry`, so adding a
new channel (SMS, push) later is a new adapter + one ``register`` call — no
business-logic change.

The email adapter is selectable by ``settings.email_provider`` (``console`` by
default — logs, no network; ``resend`` for real delivery). :class:`SesEmailAdapter`
drops in later behind the same :class:`EmailAdapter` interface.
"""
from __future__ import annotations

from app.notifications.adapters.base import (
    EmailAdapter,
    NotificationAdapter,
    SendResult,
)
from app.notifications.adapters.console import ConsoleEmailAdapter
from app.notifications.adapters.registry import (
    AdapterRegistry,
    build_email_adapter,
    default_registry,
)
from app.notifications.adapters.resend import ResendEmailAdapter

__all__ = [
    "AdapterRegistry",
    "ConsoleEmailAdapter",
    "EmailAdapter",
    "NotificationAdapter",
    "ResendEmailAdapter",
    "SendResult",
    "build_email_adapter",
    "default_registry",
]
