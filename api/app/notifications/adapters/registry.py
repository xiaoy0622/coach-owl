"""Adapter registry: maps a channel to its adapter.

The dispatcher and outbox processor resolve adapters through here, so the rest of
the codebase never imports a concrete adapter. Register a new channel's adapter
(SMS, push) and everything downstream picks it up unchanged.
"""
from __future__ import annotations

from app.core.errors import AppError
from app.models.enums import NotificationChannel
from app.notifications.adapters.base import NotificationAdapter
from app.notifications.adapters.console import ConsoleEmailAdapter


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


# Process-wide default: email -> console (MVP). Wave 3b/later swap the email
# adapter (Resend/SES) or register additional channels here.
default_registry = AdapterRegistry()
default_registry.register(ConsoleEmailAdapter())
