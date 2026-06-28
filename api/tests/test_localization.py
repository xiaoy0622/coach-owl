"""Localization: AUD formatting, GST calc, AU dates, DST-correct tz."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.utils.localization import (
    calc_gst,
    format_aud,
    format_date_au,
    to_org_timezone,
)


def test_format_aud():
    assert format_aud(Decimal("1234.5")) == "$1,234.50"
    assert format_aud(0) == "$0.00"
    assert format_aud("9.999") == "$10.00"  # rounds half-up
    assert format_aud(-5) == "-$5.00"
    assert format_aud(1000, symbol=False) == "1,000.00"


def test_gst_enabled():
    b = calc_gst("100.00", gst_enabled=True, gst_rate="0.10")
    assert b.subtotal == Decimal("100.00")
    assert b.gst_amount == Decimal("10.00")
    assert b.total == Decimal("110.00")


def test_gst_disabled():
    b = calc_gst("100.00", gst_enabled=False)
    assert b.gst_amount == Decimal("0.00")
    assert b.total == Decimal("100.00")


def test_gst_rounding_half_up():
    # 99.99 * 0.10 = 9.999 -> 10.00
    b = calc_gst("99.99", gst_enabled=True, gst_rate="0.10")
    assert b.gst_amount == Decimal("10.00")
    assert b.total == Decimal("109.99")


def test_format_date_au():
    assert format_date_au(datetime(2026, 3, 7)) == "07/03/2026"


def test_timezone_dst_correct():
    # Sydney is UTC+11 during daylight saving (January) and UTC+10 in winter (July).
    summer = to_org_timezone(
        datetime(2026, 1, 15, 2, 0, tzinfo=UTC), "Australia/Sydney"
    )
    winter = to_org_timezone(
        datetime(2026, 7, 15, 2, 0, tzinfo=UTC), "Australia/Sydney"
    )
    assert summer.hour == 13  # +11
    assert winter.hour == 12  # +10
