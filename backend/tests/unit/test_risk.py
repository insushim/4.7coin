"""Risk-layer unit tests.

These tests fence the critical guardrails. Kill-switch and drawdown boundaries
must NOT regress.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from quantsage.risk import kelly_fraction, size_position, volatility_target_fraction
from quantsage.risk.black_swan import BlackSwanDetector
from quantsage.risk.drawdown_guard import DrawdownGuard, DrawdownSnapshot
from quantsage.risk.kill_switch import KillReason, KillSwitch


def test_kelly_fraction_caps_at_zero_when_negative() -> None:
    assert kelly_fraction(0.3, 1.0, 0.25) == 0.0


def test_kelly_fraction_monotonic_win_rate() -> None:
    low = kelly_fraction(0.5, 1.5, 0.25)
    high = kelly_fraction(0.65, 1.5, 0.25)
    assert high > low


def test_vol_target_caps_at_one() -> None:
    assert volatility_target_fraction(0.01, 0.20) == 1.0


def test_size_position_respects_position_cap() -> None:
    result = size_position(
        equity_krw=Decimal("10000000"),
        confidence=1.0,
        win_rate=0.6,
        payoff_ratio=2.0,
        realized_vol_annual=0.2,
        existing_notional_krw=Decimal("2500000"),  # already at 25%
    )
    assert result.notional_krw == Decimal("0")


def test_size_position_returns_positive_on_good_setup() -> None:
    result = size_position(
        equity_krw=Decimal("10000000"),
        confidence=0.8,
        win_rate=0.58,
        payoff_ratio=1.8,
        realized_vol_annual=0.3,
        existing_notional_krw=Decimal("0"),
    )
    assert result.notional_krw > 0


@pytest.mark.asyncio
async def test_kill_switch_trigger_once() -> None:
    ks = KillSwitch()
    await ks.trigger(KillReason.MANUAL, "test")
    assert ks.is_active
    await ks.trigger(KillReason.BLACK_SWAN, "should not override")
    assert ks.reason == KillReason.MANUAL
    await ks.reset()
    assert not ks.is_active


@pytest.mark.asyncio
async def test_drawdown_guard_triggers_kill_on_max_dd() -> None:
    from quantsage.risk.kill_switch import kill_switch

    await kill_switch.reset()
    guard = DrawdownGuard()
    snap = DrawdownSnapshot(
        equity_peak=Decimal("10000000"),
        equity_now=Decimal("8400000"),  # -16% cumulative
        day_start_equity=Decimal("10000000"),
        week_start_equity=Decimal("10000000"),
        day=__import__("datetime").date.today(),
    )
    ok, _ = await guard.check(snap)
    assert not ok
    assert kill_switch.is_active
    await kill_switch.reset()


@pytest.mark.asyncio
async def test_drawdown_guard_blocks_daily_without_kill() -> None:
    from quantsage.risk.kill_switch import kill_switch

    await kill_switch.reset()
    guard = DrawdownGuard()
    snap = DrawdownSnapshot(
        equity_peak=Decimal("10000000"),
        equity_now=Decimal("9650000"),  # -3.5% daily
        day_start_equity=Decimal("10000000"),
        week_start_equity=Decimal("10000000"),
        day=__import__("datetime").date.today(),
    )
    ok, reason = await guard.check(snap)
    assert not ok
    assert "daily" in reason
    assert not kill_switch.is_active


@pytest.mark.asyncio
async def test_black_swan_fires_on_flash_crash() -> None:
    from quantsage.risk.kill_switch import kill_switch

    await kill_switch.reset()
    det = BlackSwanDetector(window_seconds=300)
    det.add(1000, Decimal("100"))
    det.add(1100, Decimal("100"))
    det.add(1200, Decimal("93"))  # -7%
    ok, _ = await det.check()
    assert not ok
    assert kill_switch.is_active
    await kill_switch.reset()
