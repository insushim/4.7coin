"""ML model + MLPredictor strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantsage.features.engineering import FeatureConfig, aligned_xy
from quantsage.features.regime import Regime
from quantsage.strategies.ml_predictor import MLPredictor


def test_mlpredictor_holds_without_model() -> None:
    pred = MLPredictor(model=None)
    df = pd.DataFrame(
        {
            "open": np.linspace(100, 110, 300),
            "high": np.linspace(101, 111, 300),
            "low": np.linspace(99, 109, 300),
            "close": np.linspace(100, 110, 300),
            "volume": np.ones(300),
        }
    )
    sig = pred.generate_signal(df, Regime.BULL_TRENDING)
    assert str(sig.direction) == "HOLD"
    assert sig.reasoning == "no model loaded"


def test_xgboost_training_roundtrip() -> None:
    pytest.importorskip("xgboost")
    pytest.importorskip("sklearn")
    from quantsage.models.xgb import XGBConfig, XGBDirectionModel

    rng = np.random.default_rng(0)
    n = 1500
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    df = pd.DataFrame(
        {
            "timestamp": np.arange(n) * 3600_000,
            "open": close,
            "high": close * 1.004,
            "low": close * 0.996,
            "close": close,
            "volume": rng.uniform(1, 5, n),
        }
    )
    X, y = aligned_xy(df, FeatureConfig())
    m = XGBDirectionModel(XGBConfig(n_estimators=30, max_depth=3, n_splits=3))
    report = m.fit(X, y)
    assert len(report["cv"]) == 3
    probs = m.predict_proba(X.tail(10))
    assert probs.shape == (10, 3)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-4)
