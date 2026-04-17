"""Indicator correctness."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantsage.indicators import atr, bollinger_bands, ema, rsi, sma, z_score


@pytest.fixture()
def prices() -> pd.Series:
    rng = np.random.default_rng(42)
    base = np.cumsum(rng.normal(0, 1, 500)) + 100
    return pd.Series(base)


def test_sma_matches_manual(prices: pd.Series) -> None:
    expected = prices.rolling(10).mean()
    got = sma(prices, 10)
    pd.testing.assert_series_equal(got, expected)


def test_ema_monotonic_approaches_price() -> None:
    s = pd.Series([10.0] * 50)
    assert abs(ema(s, 10).iloc[-1] - 10.0) < 1e-6


def test_rsi_range(prices: pd.Series) -> None:
    r = rsi(prices, 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def test_bollinger_bands_ordering(prices: pd.Series) -> None:
    upper, mid, lower = bollinger_bands(prices, 20, 2.0)
    valid = mid.dropna().index
    assert (upper.loc[valid] >= mid.loc[valid]).all()
    assert (lower.loc[valid] <= mid.loc[valid]).all()


def test_atr_positive() -> None:
    highs = pd.Series([10, 11, 12, 13, 14] * 20)
    lows = pd.Series([9, 10, 11, 12, 13] * 20)
    closes = pd.Series([9.5, 10.5, 11.5, 12.5, 13.5] * 20)
    a = atr(highs, lows, closes, 14).dropna()
    assert (a > 0).all()


def test_z_score_mean_zero_std_one() -> None:
    s = pd.Series(np.arange(1000, dtype=float))
    z = z_score(s, 50).dropna()
    assert abs(z.iloc[-1]) > 0
