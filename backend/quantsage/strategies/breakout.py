"""Donchian breakout with volume confirmation.

Entry on confirmed 20-bar channel breakout with volume >= 2x 20-bar mean.
Requires breakout depth > 0.5 * ATR to filter fake-outs. In HIGH_VOL_CHOP the
confidence is halved to avoid whipsaws.
"""

from __future__ import annotations

import pandas as pd

from ..features.regime import Regime
from ..indicators import atr
from .base import AbstractStrategy, Direction, Signal


class Breakout(AbstractStrategy):
    name = "Breakout"
    allowed_regimes = tuple(Regime)

    def generate_signal(self, df: pd.DataFrame, regime: Regime) -> Signal:
        if len(df) < 30:
            return self.hold("insufficient history")

        high = df["high"]
        low = df["low"]
        close = df["close"]
        vol = df["volume"]

        donchian_high = high.rolling(20).max().shift(1).iloc[-1]
        donchian_low = low.rolling(20).min().shift(1).iloc[-1]
        atr14 = atr(high, low, close, 14).iloc[-1]
        vol_ma = vol.rolling(20).mean().iloc[-1]
        last_close = close.iloc[-1]
        last_vol = vol.iloc[-1]

        regime_damp = 0.5 if regime == Regime.HIGH_VOL_CHOP else 1.0
        vol_spike = last_vol / max(vol_ma, 1e-9)

        if (
            last_close > donchian_high
            and (last_close - donchian_high) > 0.5 * atr14
            and vol_spike >= 2.0
        ):
            conf = min(1.0, 0.5 + min(vol_spike / 4, 0.5)) * regime_damp
            return Signal(
                Direction.BUY,
                float(conf),
                f"Donchian-20 upper break, depth={last_close - donchian_high:.2f}, volx={vol_spike:.1f}",
                self.name,
            )
        if (
            last_close < donchian_low
            and (donchian_low - last_close) > 0.5 * atr14
            and vol_spike >= 2.0
        ):
            conf = min(1.0, 0.5 + min(vol_spike / 4, 0.5)) * regime_damp
            return Signal(
                Direction.SELL,
                float(conf),
                f"Donchian-20 lower break, depth={donchian_low - last_close:.2f}, volx={vol_spike:.1f}",
                self.name,
            )
        return self.hold("no breakout")
