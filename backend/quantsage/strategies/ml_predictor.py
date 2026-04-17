"""ML-based strategy that consumes an XGBoost (or LSTM) probability vector.

Loaded model is owned by the strategy instance — lets the ensemble stay
stateless. If no model is wired, the strategy always HOLDs (safe default).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..features.engineering import build_features
from ..features.regime import Regime
from ..models.xgb import XGBDirectionModel
from ..utils.logger import logger
from .base import AbstractStrategy, Direction, Signal


class MLPredictor(AbstractStrategy):
    name = "MLPredictor"
    allowed_regimes = tuple(Regime)

    def __init__(
        self,
        model: XGBDirectionModel | None = None,
        model_path: str | Path | None = None,
        up_threshold: float = 0.55,
        down_threshold: float = 0.55,
    ):
        self.model = model
        if model_path and self.model is None:
            try:
                self.model = XGBDirectionModel()
                self.model.load(model_path)
                logger.info(f"MLPredictor loaded model from {model_path}")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"MLPredictor model load failed ({exc}); staying dark")
                self.model = None
        self.up_th = up_threshold
        self.down_th = down_threshold

    def generate_signal(self, df: pd.DataFrame, regime: Regime) -> Signal:
        if self.model is None:
            return self.hold("no model loaded")
        try:
            feat = build_features(df)
            if len(feat) < 1:
                return self.hold("no features")
            probs = self.model.predict_proba(feat.tail(1))
            p_down, _p_flat, p_up = float(probs[0, 0]), float(probs[0, 1]), float(probs[0, 2])
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"MLPredictor inference failed: {exc}")
            return self.hold("inference error")

        if p_up >= self.up_th and p_up > p_down:
            conf = min(1.0, (p_up - 0.5) * 2)
            return Signal(Direction.BUY, conf, f"xgb P(up)={p_up:.2f}", self.name)
        if p_down >= self.down_th and p_down > p_up:
            conf = min(1.0, (p_down - 0.5) * 2)
            return Signal(Direction.SELL, conf, f"xgb P(down)={p_down:.2f}", self.name)
        return self.hold(f"undecided (up={p_up:.2f}, down={p_down:.2f})")
