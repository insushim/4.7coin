"""Trend-following on dual-EMA + ADX filter.

Entry: EMA50 > EMA200 AND ADX > 25 AND close pulled back to EMA21.
Confidence scales with ADX strength, damped when RSI overbought.
"""

from __future__ import annotations

import pandas as pd

from ..features.regime import Regime
from ..indicators import adx, ema, rsi
from .base import AbstractStrategy, Direction, Signal


class TrendFollowing(AbstractStrategy):
    name = "TrendFollowing"
    allowed_regimes = (Regime.BULL_TRENDING, Regime.BEAR_TRENDING)

    def generate_signal(self, df: pd.DataFrame, regime: Regime) -> Signal:
        if not self.is_regime_allowed(regime):
            return self.hold(f"regime {regime} not allowed")
        if len(df) < 210:
            return self.hold("insufficient history")

        close = df["close"]
        e21 = ema(close, 21).iloc[-1]
        e50 = ema(close, 50).iloc[-1]
        e200 = ema(close, 200).iloc[-1]
        adx14 = adx(df["high"], df["low"], close, 14).iloc[-1]
        rsi14 = rsi(close, 14).iloc[-1]
        last = close.iloc[-1]

        bull_setup = e50 > e200 and last > e21 * 0.99 and last < e21 * 1.02
        bear_setup = e50 < e200 and last < e21 * 1.01 and last > e21 * 0.98
        adx_strong = adx14 > 25

        if bull_setup and adx_strong and rsi14 < 75:
            conf = min(adx14 / 50, 1.0) * (1 - max(0, (rsi14 - 60) / 40))
            return Signal(
                Direction.BUY,
                float(conf),
                f"EMA50>EMA200, close near EMA21, ADX={adx14:.1f}, RSI={rsi14:.1f}",
                self.name,
            )
        if bear_setup and adx_strong and rsi14 > 25:
            conf = min(adx14 / 50, 1.0) * (1 - max(0, (40 - rsi14) / 40))
            return Signal(
                Direction.SELL,
                float(conf),
                f"EMA50<EMA200, close near EMA21, ADX={adx14:.1f}, RSI={rsi14:.1f}",
                self.name,
            )
        return self.hold("no trend setup")
