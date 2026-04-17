"""Walk-forward runner produces windows + renderable HTML."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantsage.backtest.report import render_html, run_walk_forward
from quantsage.strategies import default_ensemble


def _ohlcv(n: int = 2000, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0001, 0.012, n)
    price = 100 * np.cumprod(1 + returns)
    return pd.DataFrame(
        {
            "timestamp": np.arange(n) * 3600_000,
            "open": price,
            "high": price * (1 + rng.uniform(0.0, 0.004, n)),
            "low": price * (1 - rng.uniform(0.0, 0.004, n)),
            "close": price,
            "volume": rng.uniform(50, 200, n),
        }
    )


def test_walk_forward_produces_windows_and_aggregate() -> None:
    df = _ohlcv(1600)
    windows, aggregate = run_walk_forward(
        df, default_ensemble(), train_bars=600, test_bars=300, step_bars=300
    )
    assert len(windows) >= 1
    assert aggregate.n_trades >= 0
    for w in windows:
        assert w.end_bar - w.start_bar == 300


def test_render_html_self_contained() -> None:
    df = _ohlcv(1200)
    windows, aggregate = run_walk_forward(
        df, default_ensemble(), train_bars=500, test_bars=250, step_bars=250
    )
    html = render_html(windows, aggregate, symbol="TEST", timeframe="1h")
    assert "<!doctype html>" in html.lower()
    assert "Walk-Forward" in html
    assert "Validation Checklist" in html
