"""XGBoost classifier for 3-class direction.

Kept deliberately small and deterministic — better to ship a solid baseline
than a brittle SOTA. Training is chronological (TimeSeriesSplit) to prevent
look-ahead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..features.engineering import FeatureConfig, aligned_xy
from ..utils.logger import logger


@dataclass
class XGBConfig:
    n_estimators: int = 200
    max_depth: int = 4
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: int = 3
    reg_lambda: float = 1.0
    objective: str = "multi:softprob"
    num_class: int = 3
    random_state: int = 42
    n_splits: int = 5


class XGBDirectionModel:
    """Thin wrapper with probabilistic outputs + feature-importance export."""

    def __init__(self, cfg: XGBConfig | None = None):
        self.cfg = cfg or XGBConfig()
        self._model = None
        self._feature_names: list[str] = []

    def _new_booster(self):
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError("xgboost not installed. `pip install xgboost`") from exc
        return XGBClassifier(
            n_estimators=self.cfg.n_estimators,
            max_depth=self.cfg.max_depth,
            learning_rate=self.cfg.learning_rate,
            subsample=self.cfg.subsample,
            colsample_bytree=self.cfg.colsample_bytree,
            min_child_weight=self.cfg.min_child_weight,
            reg_lambda=self.cfg.reg_lambda,
            objective=self.cfg.objective,
            num_class=self.cfg.num_class,
            random_state=self.cfg.random_state,
            tree_method="hist",
            eval_metric="mlogloss",
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> dict:
        from sklearn.metrics import accuracy_score, log_loss
        from sklearn.model_selection import TimeSeriesSplit

        self._feature_names = list(X.columns)
        cv = TimeSeriesSplit(n_splits=self.cfg.n_splits)
        scores = []
        for i, (tr, vl) in enumerate(cv.split(X)):
            m = self._new_booster()
            m.fit(X.iloc[tr], y.iloc[tr])
            p = m.predict_proba(X.iloc[vl])
            try:
                ll = log_loss(y.iloc[vl], p, labels=[0, 1, 2])
            except ValueError:
                ll = float("nan")
            acc = accuracy_score(y.iloc[vl], p.argmax(axis=1))
            logger.info(f"xgb fold {i+1}/{self.cfg.n_splits}: logloss={ll:.4f} acc={acc:.3f}")
            scores.append({"fold": i, "logloss": ll, "acc": acc})
        # final fit on full set
        self._model = self._new_booster()
        self._model.fit(X, y)
        return {"cv": scores, "n_features": len(self._feature_names)}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("model not fitted")
        X2 = X[self._feature_names]  # enforce column order
        return self._model.predict_proba(X2)

    def predict_up_probability(self, X: pd.DataFrame) -> np.ndarray:
        """Shortcut for the class-2 (UP) column."""
        return self.predict_proba(X)[:, 2]

    def feature_importance(self, top_k: int = 20) -> list[tuple[str, float]]:
        if self._model is None:
            return []
        imp = self._model.feature_importances_
        pairs = sorted(zip(self._feature_names, imp), key=lambda p: p[1], reverse=True)
        return pairs[:top_k]

    def save(self, path: str | Path) -> None:
        if self._model is None:
            raise RuntimeError("model not fitted")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._model.save_model(str(p))
        (p.with_suffix(".json.meta")).write_text(
            json.dumps({"features": self._feature_names}, ensure_ascii=False)
        )

    def load(self, path: str | Path) -> None:
        from xgboost import XGBClassifier

        p = Path(path)
        m = XGBClassifier()
        m.load_model(str(p))
        self._model = m
        meta = (p.with_suffix(".json.meta")).read_text()
        self._feature_names = json.loads(meta)["features"]


def train_on_ohlcv(
    df: pd.DataFrame,
    feature_cfg: FeatureConfig | None = None,
    model_cfg: XGBConfig | None = None,
) -> tuple[XGBDirectionModel, dict]:
    X, y = aligned_xy(df, feature_cfg)
    m = XGBDirectionModel(model_cfg)
    report = m.fit(X, y)
    report["importance_top20"] = m.feature_importance(20)
    return m, report
