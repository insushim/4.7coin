"""Live executor refuses to act when live mode is disabled."""

from __future__ import annotations

from decimal import Decimal
from typing import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from quantsage.exchanges.base import AbstractExchange, Ticker
from quantsage.execution.live import ExecutionConfig, LiveExecutor
from quantsage.features.regime import Regime
from quantsage.risk.aggregator import OrderProposal, RiskAggregator, RiskContext
from quantsage.risk.black_swan import BlackSwanDetector
from quantsage.risk.kill_switch import kill_switch
from quantsage.strategies.base import Direction


class _FakeExchange(AbstractExchange):
    name = "fake"

    async def fetch_ohlcv(self, symbol, timeframe="1m", limit=200):
        return []

    async def fetch_ticker(self, symbol):
        return Ticker(symbol, Decimal("1"), Decimal("1"), Decimal("1"), 0)

    async def fetch_orderbook(self, symbol, depth=10):
        return {"symbol": symbol, "bids": [], "asks": [], "timestamp": 0}

    async def fetch_balance(self):
        return {}

    async def create_order(self, *args, **kwargs):
        raise AssertionError("should not be called while live disabled")

    async def cancel_order(self, order_id):
        return True

    async def fetch_open_orders(self, symbol=None):
        return []

    async def fetch_markets(self):
        return []

    async def stream_ticker(self, symbols) -> AsyncIterator[Ticker]:  # pragma: no cover
        if False:
            yield  # type: ignore[unreachable]


@pytest.mark.asyncio
async def test_live_executor_refuses_when_disabled() -> None:
    await kill_switch.reset()
    fake = _FakeExchange()
    risk = RiskAggregator()
    live = LiveExecutor(fake, risk, config=ExecutionConfig())

    proposal = OrderProposal(
        symbol="KRW-BTC",
        direction=Direction.BUY,
        confidence=0.9,
        strategy="test",
        regime=Regime.BULL_TRENDING,
        reasoning="test",
    )

    async def _ctx() -> RiskContext:
        return RiskContext(
            equity_krw=Decimal("10000000"),
            day_start_equity=Decimal("10000000"),
            week_start_equity=Decimal("10000000"),
            equity_peak=Decimal("10000000"),
            existing_positions={},
            correlation_map={},
            realized_vol_annual=0.3,
            orderbook_depth_krw=Decimal("100000000"),
            allowed_strategies_by_regime={r: set() for r in Regime},
            black_swan=BlackSwanDetector(),
        )

    result = await live.submit(proposal, _ctx, reference_price=Decimal("100000000"))
    assert result.accepted is False
    assert "TRADING_MODE" in result.reason or "ENABLE_LIVE_TRADING" in result.reason


@pytest.mark.asyncio
async def test_live_executor_raises_when_kill_active() -> None:
    await kill_switch.reset()
    fake = _FakeExchange()
    live = LiveExecutor(fake, RiskAggregator())

    from quantsage.risk.kill_switch import KillReason

    await kill_switch.trigger(KillReason.MANUAL, "test")

    proposal = OrderProposal(
        symbol="KRW-BTC",
        direction=Direction.BUY,
        confidence=0.9,
        strategy="t",
        regime=Regime.BULL_TRENDING,
        reasoning="t",
    )

    async def _ctx() -> RiskContext:
        return RiskContext(
            equity_krw=Decimal("10000000"),
            day_start_equity=Decimal("10000000"),
            week_start_equity=Decimal("10000000"),
            equity_peak=Decimal("10000000"),
            existing_positions={},
            correlation_map={},
            realized_vol_annual=0.3,
            orderbook_depth_krw=Decimal("100000000"),
            allowed_strategies_by_regime={r: set() for r in Regime},
            black_swan=BlackSwanDetector(),
        )

    from quantsage.exceptions import KillSwitchActive

    with pytest.raises(KillSwitchActive):
        await live.submit(proposal, _ctx, reference_price=Decimal("100000000"))
    await kill_switch.reset()
