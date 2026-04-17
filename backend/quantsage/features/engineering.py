"""Feature engineering for ML strategies.

~45 features: price derivatives, indicator outputs + their deltas, volatility,
time cyclical encodings. Target = 1 if next-bar log-return > threshold else 0
(binary directional), configurable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..indicators import (
    adx,
    atr,
    bollinger_bands,
    ema,
    macd,
    rsi,
    sma,
    stochastic,
    z_score,
)


@dataclass
class FeatureConfig:
    horizon_bars: int = 1          # predict next bar direction
    up_threshold: float = 0.002    # +0.2% = "up"
    down_threshold: float = -0.002


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return feature matrix with NaNs dropped."""
    if not {"open", "high", "low", "close", "volume"}.issubset(df.columns):
        raise ValueError("df must have OHLCV columns")
    f = pd.DataFrame(index=df.index)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"]

    # returns at multiple horizons
    for k in (1, 5, 15, 60):
        f[f"ret_{k}"] = np.log(close).diff(k)

    # moving averages + ratios
    for p in (5, 20, 50, 200):
        f[f"sma_{p}_ratio"] = close / sma(close, p)
        f[f"ema_{p}_ratio"] = close / ema(close, p)
    f["ema_50_200_diff"] = (ema(close, 50) - ema(close, 200)) / close

    # momentum
    f["rsi_14"] = rsi(close, 14)
    f["stoch_14"] = stochastic(high, low, close, 14)
    macd_line, sig, hist = macd(close)
    f["macd_hist"] = hist
    f["macd_line"] = macd_line

    # volatility
    upper, mid, lower = bollinger_bands(close, 20, 2.0)
    f["bb_pct"] = (close - lower) / (upper - lower)
    f["bb_width"] = (upper - lower) / mid
    f["atr_14_ratio"] = atr(high, low, close, 14) / close

    # trend strength
    f["adx_14"] = adx(high, low, close, 14)

    # range position / mean reversion
    f["zscore_20"] = z_score(close, 20)

    # volume
    f["vol_z_20"] = z_score(vol, 20)
    f["vol_sma_20_ratio"] = vol / sma(vol, 20)

    # realized vol
    f["rv_30"] = np.log(close).diff().rolling(30).std() * np.sqrt(30)
    f["rv_90"] = np.log(close).diff().rolling(90).std() * np.sqrt(90)

    # time cyclical
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        hour = ts.dt.hour
        dow = ts.dt.dayofweek
        f["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        f["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        f["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        f["dow_cos"] = np.cos(2 * np.pi * dow / 7)

    return f.replace([np.inf, -np.inf], np.nan).dropna()


def build_target(df: pd.DataFrame, cfg: FeatureConfig | None = None) -> pd.Series:
    """Binary {0, 1, 2} target: 0=down, 1=flat, 2=up.

    Return ties broken to flat so thresholds are disjoint.
    """
    cfg = cfg or FeatureConfig()
    close = df["close"]
    future = np.log(close).shift(-cfg.horizon_bars) - np.log(close)
    target = pd.Series(1, index=close.index)  # flat
    target[future >= cfg.up_threshold] = 2
    target[future <= cfg.down_threshold] = 0
    return target


def aligned_xy(df: pd.DataFrame, cfg: FeatureConfig | None = None) -> tuple[pd.DataFrame, pd.Series]:
    cfg = cfg or FeatureConfig()
    features = build_features(df)
    target = build_target(df, cfg).loc[features.index]
    # drop last horizon_bars — unknown future
    valid = ~target.isna()
    features = features.loc[valid].iloc[: -cfg.horizon_bars or len(features)]
    target = target.loc[valid].iloc[: -cfg.horizon_bars or len(target)]
    return features, target.astype(int)
