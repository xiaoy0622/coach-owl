"""Adapter registry: maps a channel to its adapter.

The dispatcher and outbox processor resolve adapters through here, so the rest of
the codebase never imports a concrete adapter. Register a new channel's adapter
(SMS, push) and everything downstream picks it up unchanged.
"""
from __future__ import annotations

import logging

from app.core.config import settings
from app.core.errors import AppError
from app.models.enums import NotificationChannel
from app.notifications.adapters.base import EmailAdapter, NotificationAdapter
from app.notifications.adapters.console import ConsoleEmailAdapter
from app.notifications.adapters.resend import ResendEmailAdapter

logger = logging.getLogger("coachowl.notifications.email")


class AdapterRegistry:
    """channel -> adapter lookup."""

    def __init__(self) -> None:
        self._adapters: dict[NotificationChannel, NotificationAdapter] = {}

    def register(self, adapter: NotificationAdapter) -> None:
        """Register (or replace) the adapter for ``adapter.channel``."""
        self._adapters[adapter.channel] = adapter

    def get(self, channel: NotificationChannel) -> NotificationAdapter:
        adapter = self._adapters.get(channel)
        if adapter is None:
            raise AppError(
                f"No adapter registered for channel '{channel.value}'",
                code="no_adapter",
                status_code=500,
            )
        return adapter

    def channels(self) -> list[NotificationChannel]:
        return list(self._adapters)


# email_provider value -> adapter factory. A future SES adapter is one entry here
# (``"ses": SesEmailAdapter``) plus the config value — nothing else changes.
_EMAIL_ADAPTERS: dict[str, type[EmailAdapter]] = {
    "console": ConsoleEmailAdapter,
    "resend": ResendEmailAdapter,
}


def build_email_adapter(provider: str | None = None) -> EmailAdapter:
    """Return the email adapter for ``provider`` (defaults to settings).

    Unknown providers fall back to the console adapter with a warning so a
    misconfiguration degrades safely instead of crashing process startup.
    """
    name = (provider or settings.email_provider or "console").lower()
    adapter_cls = _EMAIL_ADAPTERS.get(name)
    if adapter_cls is None:
        logger.warning(
            "Unknown email_provider %r; falling back to console adapter", name
        )
        adapter_cls = ConsoleEmailAdapter
    return adapter_cls()


# Process-wide default. The email adapter is chosen by ``settings.email_provider``
# (default ``console`` — logs only, no key). Set it to ``resend`` to deliver for
# real; add another channel (SMS, push) with a further ``register`` call.
default_registry = AdapterRegistry()
default_registry.register(build_email_adapter())
