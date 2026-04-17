"""Market regime detection.

Four regimes: BULL_TRENDING / BEAR_TRENDING / RANGE / HIGH_VOL_CHOP.
Uses 200-day SMA position, ADX strength, and realized vs mean volatility.
"""

from __future__ import annotations

from enum import StrEnum

import numpy as np
import pandas as pd

from ..indicators import adx, sma


class Regime(StrEnum):
    BULL_TRENDING = "BULL_TRENDING"
    BEAR_TRENDING = "BEAR_TRENDING"
    RANGE = "RANGE"
    HIGH_VOL_CHOP = "HIGH_VOL_CHOP"


def detect_regime(
    df: pd.DataFrame, vol_lookback: int = 30, vol_ref_window: int = 90
) -> Regime:
    """Classify the current regime from OHLCV.

    `df` must have columns: high, low, close. Index monotonic ascending.
    """
    close = df["close"]
    returns = close.pct_change()

    sma_200 = sma(close, 200)
    adx_14 = adx(df["high"], df["low"], close, 14)

    realized_vol = returns.rolling(vol_lookback).std().iloc[-1]
    mean_vol = returns.rolling(vol_ref_window).std().mean()

    if pd.isna(sma_200.iloc[-1]) or pd.isna(adx_14.iloc[-1]):
        return Regime.RANGE

    last_close = close.iloc[-1]
    last_sma = sma_200.iloc[-1]
    last_adx = adx_14.iloc[-1]

    # High-vol chop blocks directional strategies
    if not np.isnan(realized_vol) and not np.isnan(mean_vol):
        if realized_vol > mean_vol * 1.5:
            return Regime.HIGH_VOL_CHOP

    if last_close > last_sma * 1.03 and last_adx > 22:
        return Regime.BULL_TRENDING
    if last_close < last_sma * 0.97 and last_adx > 22:
        return Regime.BEAR_TRENDING
    return Regime.RANGE
