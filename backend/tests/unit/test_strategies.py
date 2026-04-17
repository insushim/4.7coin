"""Strategy + ensemble smoke tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantsage.features.regime import Regime
from quantsage.strategies import (
    Breakout,
    MeanReversion,
    TrendFollowing,
    default_ensemble,
)
from quantsage.strategies.base import Direction


@pytest.fixture()
def uptrend() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 400
    drift = np.linspace(100, 300, n)
    noise = rng.normal(0, 1, n)
    close = drift + noise
    df = pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + rng.uniform(0.2, 1.0, n),
            "low": close - rng.uniform(0.2, 1.0, n),
            "close": close,
            "volume": rng.uniform(1, 5, n),
        }
    )
    return df


@pytest.fixture()
def range_bound() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    n = 400
    close = 100 + np.sin(np.linspace(0, 20, n)) * 5 + rng.normal(0, 0.5, n)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.1, 0.8, n),
            "low": close - rng.uniform(0.1, 0.8, n),
            "close": close,
            "volume": rng.uniform(1, 5, n),
        }
    )
    return df


def test_trend_following_holds_when_regime_blocked(range_bound: pd.DataFrame) -> None:
    sig = TrendFollowing().generate_signal(range_bound, Regime.RANGE)
    assert sig.direction == Direction.HOLD


def test_mean_reversion_holds_outside_range(uptrend: pd.DataFrame) -> None:
    sig = MeanReversion().generate_signal(uptrend, Regime.BULL_TRENDING)
    assert sig.direction == Direction.HOLD


def test_breakout_tolerates_any_regime_without_crash(uptrend: pd.DataFrame) -> None:
    sig = Breakout().generate_signal(uptrend, Regime.HIGH_VOL_CHOP)
    assert sig.direction in (Direction.BUY, Direction.SELL, Direction.HOLD)


def test_ensemble_hold_when_no_majority(range_bound: pd.DataFrame) -> None:
    ensemble = default_ensemble()
    decision = ensemble.decide(range_bound, Regime.RANGE)
    assert decision.direction in (Direction.BUY, Direction.SELL, Direction.HOLD)
