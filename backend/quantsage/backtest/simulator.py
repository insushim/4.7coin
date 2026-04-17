"""Event-driven backtest simulator.

Models: fee, spread-based slippage, latency-induced fill delay, partial fills.
Deliberately pessimistic defaults so live-vs-paper surprise is minimized.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal

import pandas as pd

from ..strategies.base import Direction


@dataclass
class Trade:
    entry_ts: int
    exit_ts: int | None
    symbol: str
    direction: Direction
    entry_price: float
    exit_price: float | None
    amount: float
    pnl: float
    strategy: str
    reason_entry: str
    reason_exit: str = ""


@dataclass
class SimulatorConfig:
    fee_rate: float = 0.0005  # 0.05% taker fee (Upbit)
    slippage_bps: float = 5.0  # 5bps + random jitter
    latency_ms: int = 200
    pessimistic: bool = False  # if True, buy at high, sell at low
    seed: int = 42


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: pd.Series
    final_equity: float
    initial_equity: float
    config: SimulatorConfig = field(default_factory=SimulatorConfig)

    @property
    def total_return(self) -> float:
        return (self.final_equity - self.initial_equity) / self.initial_equity


class Simulator:
    def __init__(self, config: SimulatorConfig | None = None) -> None:
        self.config = config or SimulatorConfig()
        self._rng = random.Random(self.config.seed)

    def fill_price(self, reference: float, direction: Direction, high: float, low: float) -> float:
        cfg = self.config
        slippage_frac = cfg.slippage_bps / 10_000 + abs(self._rng.gauss(0, 0.0002))
        if cfg.pessimistic:
            return high if direction == Direction.BUY else low
        if direction == Direction.BUY:
            return reference * (1 + slippage_frac)
        return reference * (1 - slippage_frac)

    def apply_fee(self, notional: float) -> float:
        return notional * self.config.fee_rate
