"""Main trading loop.

Periodically: fetch OHLCV → detect regime → ensemble vote → risk check →
paper/live execution. Exceptions never crash the loop — they log and continue.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from ..config import settings
from ..exchanges import AbstractExchange, create_exchange
from ..exchanges.base import Candle
from ..execution.dry_run import PaperExecutor
from ..features.regime import Regime, detect_regime
from ..risk.aggregator import OrderProposal, RiskAggregator, RiskContext
from ..risk.black_swan import BlackSwanDetector
from ..risk.kill_switch import kill_switch
from ..strategies import default_ensemble
from ..strategies.base import Direction
from ..utils.logger import logger


def candles_to_df(candles: list[Candle]) -> pd.DataFrame:
    rows = [
        {
            "timestamp": c.timestamp,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume),
        }
        for c in candles
    ]
    df = pd.DataFrame(rows)
    return df.sort_values("timestamp").reset_index(drop=True)


@dataclass
class LoopState:
    running: bool = False
    last_regime: Regime | None = None
    last_error: str = ""
    iterations: int = 0


class MainLoop:
    def __init__(
        self,
        symbols: list[str],
        exchange: AbstractExchange | None = None,
        paper: PaperExecutor | None = None,
    ):
        self.symbols = symbols
        self.exchange = exchange or create_exchange("upbit")
        self.paper = paper or PaperExecutor()
        self.ensemble = default_ensemble()
        self.risk = RiskAggregator(min_confidence=settings.min_confidence)
        self.black_swan = BlackSwanDetector()
        self.state = LoopState()

    async def _handle_symbol(self, symbol: str) -> None:
        candles = await self.exchange.fetch_ohlcv(symbol, "1h", 300)
        if len(candles) < 210:
            logger.info(f"{symbol}: insufficient history ({len(candles)})")
            return
        df = candles_to_df(candles)
        regime = detect_regime(df)
        self.state.last_regime = regime
        decision = self.ensemble.decide(df, regime)
        logger.info(f"{symbol} regime={regime} decision={decision.direction} conf={decision.confidence:.2f}")

        if decision.direction == Direction.HOLD:
            return

        last_price = Decimal(str(df["close"].iloc[-1]))
        equity_marks = {symbol: last_price}
        equity = self.paper.equity_krw(equity_marks)
        existing = {
            s: qty * last_price for s, qty in self.paper.account.positions.items() if qty > 0
        }

        proposal = OrderProposal(
            symbol=symbol,
            direction=decision.direction,
            confidence=decision.confidence,
            strategy="ensemble",
            regime=regime,
            reasoning=decision.reasoning,
        )
        ctx = RiskContext(
            equity_krw=equity,
            day_start_equity=equity,
            week_start_equity=equity,
            equity_peak=equity,
            existing_positions=existing,
            correlation_map={},
            realized_vol_annual=float(df["close"].pct_change().std() * (252 * 24) ** 0.5),
            orderbook_depth_krw=Decimal("100000000"),
            allowed_strategies_by_regime={r: set() for r in Regime},
            black_swan=self.black_swan,
        )
        self.black_swan.add(df["timestamp"].iloc[-1] // 1000, last_price)

        result = await self.risk.evaluate(proposal, ctx)
        if not result.allowed:
            logger.info(f"{symbol} blocked at {result.blocked_layer}: {result.reason}")
            return

        if settings.is_live:
            logger.warning(f"{symbol} live execution not yet enabled in this build")
            return

        side = "buy" if decision.direction == Direction.BUY else "sell"
        try:
            if side == "buy":
                await self.paper.create_order(
                    symbol=symbol,
                    side="buy",
                    order_type="market",
                    amount=result.sizing.notional_krw,
                    reference_price=last_price,
                    strategy="ensemble",
                    reasoning=decision.reasoning,
                )
            else:
                qty = self.paper.account.positions.get(symbol, Decimal("0"))
                if qty > 0:
                    await self.paper.create_order(
                        symbol=symbol,
                        side="sell",
                        order_type="market",
                        amount=qty,
                        reference_price=last_price,
                        strategy="ensemble",
                        reasoning=decision.reasoning,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"{symbol} execution error: {exc}")

    async def tick(self) -> None:
        if kill_switch.is_active:
            logger.warning(f"Kill-switch active: {kill_switch.message}")
            return
        for symbol in self.symbols:
            try:
                await self._handle_symbol(symbol)
            except Exception as exc:  # noqa: BLE001
                self.state.last_error = str(exc)
                logger.exception(f"{symbol}: loop error")
        self.state.iterations += 1

    async def run(self, interval_seconds: int = 3600) -> None:
        self.state.running = True
        logger.info(f"MainLoop starting for {self.symbols}, interval={interval_seconds}s")
        while self.state.running and not kill_switch.is_active:
            await self.tick()
            await asyncio.sleep(interval_seconds)

    def stop(self) -> None:
        self.state.running = False
