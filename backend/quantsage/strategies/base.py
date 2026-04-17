"""Strategy abstraction.

A strategy consumes an OHLCV DataFrame and returns a Signal. Signals do NOT
size positions — that is the risk/position-sizer's job. This separation keeps
strategies testable in isolation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from ..features.regime import Regime


class Direction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    direction: Direction
    confidence: float  # 0..1
    reasoning: str
    strategy: str


class AbstractStrategy(ABC):
    name: str = "abstract"
    allowed_regimes: tuple[Regime, ...] = tuple(Regime)

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, regime: Regime) -> Signal:
        """Return the strategy's decision for the latest bar."""

    def is_regime_allowed(self, regime: Regime) -> bool:
        return regime in self.allowed_regimes

    def hold(self, reason: str = "regime blocked") -> Signal:
        return Signal(Direction.HOLD, 0.0, reason, self.name)
