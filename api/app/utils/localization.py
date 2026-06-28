"""Australian localization helpers: AUD money, GST, DD/MM/YYYY + timezone.

Money is handled as ``Decimal`` and rounded half-up to cents. GST honours the
org's ``gst_enabled`` flag; when disabled, gst is 0 and total == subtotal.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

CENTS = Decimal("0.01")


def to_decimal(value: Decimal | int | float | str) -> Decimal:
    """Coerce to Decimal without binary-float surprises."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_money(amount: Decimal | int | float | str) -> Decimal:
    return to_decimal(amount).quantize(CENTS, rounding=ROUND_HALF_UP)


def format_aud(amount: Decimal | int | float | str, *, symbol: bool = True) -> str:
    """Format a value as AUD, e.g. ``$1,234.50`` (or ``1,234.50``)."""
    cents = round_money(amount)
    sign = "-" if cents < 0 else ""
    whole = abs(cents)
    text = f"{whole:,.2f}"
    return f"{sign}{'$' if symbol else ''}{text}"


@dataclass(frozen=True)
class GstBreakdown:
    subtotal: Decimal
    gst_amount: Decimal
    total: Decimal


def calc_gst(
    subtotal: Decimal | int | float | str,
    *,
    gst_enabled: bool,
    gst_rate: Decimal | int | float | str = Decimal("0.10"),
) -> GstBreakdown:
    """Compute subtotal -> gst -> total. GST is 0 when disabled.

    Convention: ``subtotal`` is GST-exclusive; gst is added on top.
    """
    sub = round_money(subtotal)
    if not gst_enabled:
        return GstBreakdown(subtotal=sub, gst_amount=round_money(0), total=sub)
    gst = round_money(sub * to_decimal(gst_rate))
    return GstBreakdown(subtotal=sub, gst_amount=gst, total=round_money(sub + gst))


def format_date_au(dt: datetime) -> str:
    """DD/MM/YYYY."""
    return dt.strftime("%d/%m/%Y")


def format_datetime_au(dt: datetime) -> str:
    """DD/MM/YYYY HH:MM."""
    return dt.strftime("%d/%m/%Y %H:%M")


def to_org_timezone(dt: datetime, tz_name: str) -> datetime:
    """Render a UTC (or naive-UTC) datetime in the org's timezone (DST-correct)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ZoneInfo(tz_name))


def now_utc() -> datetime:
    return datetime.now(UTC)
