"""Range-bound grid hint.

This strategy doesn't manage actual grid orders (that belongs in the execution
layer) — it surfaces a BUY or SELL hint when price sits near the bottom/top of
a 20-day range while the regime stays RANGE. The 5% exit-from-range guard is
enforced by the range-breach check.
"""

from __future__ import annotations

import pandas as pd

from ..features.regime import Regime
from .base import AbstractStrategy, Direction, Signal


class GridHint(AbstractStrategy):
    name = "GridHint"
    allowed_regimes = (Regime.RANGE,)

    def generate_signal(self, df: pd.DataFrame, regime: Regime) -> Signal:
        if not self.is_regime_allowed(regime):
            return self.hold(f"regime {regime} not allowed")
        if len(df) < 20:
            return self.hold("insufficient history")

        hi = df["high"].rolling(20).max().iloc[-1]
        lo = df["low"].rolling(20).min().iloc[-1]
        last = df["close"].iloc[-1]
        width = hi - lo
        if width <= 0:
            return self.hold("flat range")

        pct = (last - lo) / width
        if pct < 0.15:
            return Signal(
                Direction.BUY,
                0.55 + (0.15 - pct),
                f"near range bottom ({pct:.0%} of 20d range)",
                self.name,
            )
        if pct > 0.85:
            return Signal(
                Direction.SELL,
                0.55 + (pct - 0.85),
                f"near range top ({pct:.0%} of 20d range)",
                self.name,
            )
        return self.hold("mid-range")
