"""Smart DCA with brake.

Accumulation signal when price dips >=3% from recent high while higher
time-frame regime is not BEAR. Brake engages when drawdown from entry exceeds
12% — avoids the classic DCA blow-up pattern.
"""

from __future__ import annotations

import pandas as pd

from ..features.regime import Regime
from .base import AbstractStrategy, Direction, Signal


class SmartDCA(AbstractStrategy):
    name = "SmartDCA"
    allowed_regimes = (Regime.BULL_TRENDING, Regime.RANGE)

    def generate_signal(self, df: pd.DataFrame, regime: Regime) -> Signal:
        if not self.is_regime_allowed(regime):
            return self.hold(f"regime {regime} not allowed")
        if len(df) < 50:
            return self.hold("insufficient history")

        close = df["close"]
        recent_high = close.rolling(20).max().iloc[-1]
        last = close.iloc[-1]
        dd_from_high = (last - recent_high) / recent_high

        if dd_from_high < -0.12:
            return self.hold(f"brake engaged (drawdown {dd_from_high:.0%})")

        if dd_from_high <= -0.03:
            # Sizing tiers: -3% base, -6% double, -10% triple (reflected in confidence)
            tier = 1 + int(abs(dd_from_high) // 0.03)
            conf = min(0.4 + 0.15 * tier, 0.9)
            return Signal(
                Direction.BUY,
                conf,
                f"DCA tier {tier} (dip {dd_from_high:.1%} from 20d high)",
                self.name,
            )
        return self.hold(f"no dip ({dd_from_high:.1%} from high)")
