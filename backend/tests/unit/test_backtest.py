"""Backtest engine end-to-end on synthetic data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantsage.backtest import BacktestEngine, EngineConfig
from quantsage.strategies import default_ensemble


def _make_ohlcv(n: int = 1200, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0002, 0.012, n)
    price = 100 * np.cumprod(1 + returns)
    df = pd.DataFrame(
        {
            "timestamp": np.arange(n) * 3600_000,
            "open": price,
            "high": price * (1 + rng.uniform(0.0, 0.005, n)),
            "low": price * (1 - rng.uniform(0.0, 0.005, n)),
            "close": price,
            "volume": rng.uniform(50, 200, n),
        }
    )
    return df


def test_backtest_runs_without_errors() -> None:
    df = _make_ohlcv()
    engine = BacktestEngine(default_ensemble(), engine_config=EngineConfig(initial_equity=1_000_000))
    result, metrics = engine.run(df)
    assert metrics.n_trades >= 0
    assert result.final_equity > 0
    assert len(result.equity_curve) == len(df)
