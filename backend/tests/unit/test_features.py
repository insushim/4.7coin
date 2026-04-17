"""Feature engineering / target alignment."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantsage.features.engineering import FeatureConfig, aligned_xy, build_features, build_target


def _synthetic(n: int = 500, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    return pd.DataFrame(
        {
            "timestamp": np.arange(n) * 3600_000,
            "open": close,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": rng.uniform(1, 5, n),
        }
    )


def test_build_features_returns_nonempty_matrix() -> None:
    df = _synthetic()
    feat = build_features(df)
    assert not feat.empty
    assert feat.isna().sum().sum() == 0
    assert "rsi_14" in feat.columns
    assert "bb_pct" in feat.columns


def test_build_target_tricolor() -> None:
    df = _synthetic()
    t = build_target(df, FeatureConfig(horizon_bars=1, up_threshold=0.01, down_threshold=-0.01))
    assert set(t.dropna().unique()).issubset({0, 1, 2})


def test_aligned_xy_shapes_match() -> None:
    df = _synthetic(n=800)
    X, y = aligned_xy(df)
    assert len(X) == len(y)
    assert len(X) > 0
