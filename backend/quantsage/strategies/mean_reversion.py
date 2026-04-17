"""Mean-reversion on BB + Z-score + RSI oversold.

Only activates in RANGE regime. Hurst < 0.5 boosts confidence (mean-reverting
nature). Exit is BB midline.
"""

from __future__ import annotations

import math

import pandas as pd

from ..features.regime import Regime
from ..indicators import bollinger_bands, hurst_exponent, rsi, z_score
from .base import AbstractStrategy, Direction, Signal


class MeanReversion(AbstractStrategy):
    name = "MeanReversion"
    allowed_regimes = (Regime.RANGE,)

    def generate_signal(self, df: pd.DataFrame, regime: Regime) -> Signal:
        if not self.is_regime_allowed(regime):
            return self.hold(f"regime {regime} not allowed")
        if len(df) < 100:
            return self.hold("insufficient history")

        close = df["close"]
        upper, mid, lower = bollinger_bands(close, 20, 2.0)
        rsi14 = rsi(close, 14).iloc[-1]
        zs = z_score(close, 20).iloc[-1]
        last = close.iloc[-1]
        hurst = hurst_exponent(close.tail(200), max_lag=50)

        hurst_boost = 1.0 if math.isnan(hurst) else max(0.5, 1.5 - hurst)

        if last <= lower.iloc[-1] and rsi14 < 30 and zs < -1.8:
            conf = min(1.0, (30 - rsi14) / 30 * 0.6 + abs(zs) / 4) * hurst_boost
            return Signal(
                Direction.BUY,
                float(min(conf, 1.0)),
                f"BB-lower touch, RSI={rsi14:.1f}, Z={zs:.2f}, Hurst={hurst:.2f}",
                self.name,
            )
        if last >= upper.iloc[-1] and rsi14 > 70 and zs > 1.8:
            conf = min(1.0, (rsi14 - 70) / 30 * 0.6 + abs(zs) / 4) * hurst_boost
            return Signal(
                Direction.SELL,
                float(min(conf, 1.0)),
                f"BB-upper touch, RSI={rsi14:.1f}, Z={zs:.2f}, Hurst={hurst:.2f}",
                self.name,
            )
        return self.hold("no mean-reversion setup")
