from pathlib import Path

from .base import AbstractStrategy, Direction, Signal
from .breakout import Breakout
from .dca_smart import SmartDCA
from .ensemble_voter import EnsembleDecision, EnsembleVoter
from .grid import GridHint
from .mean_reversion import MeanReversion
from .ml_predictor import MLPredictor
from .trend_following import TrendFollowing


def default_ensemble(ml_model_path: str | Path | None = "data/models/xgb.json") -> EnsembleVoter:
    """Bundle the 5 rule-based strategies + ML predictor if a model exists.

    If no trained model is at `ml_model_path`, MLPredictor stays in HOLD mode,
    which is harmless — the other five still drive decisions.
    """
    strategies: list[AbstractStrategy] = [
        TrendFollowing(),
        MeanReversion(),
        Breakout(),
        GridHint(),
        SmartDCA(),
    ]
    if ml_model_path and Path(ml_model_path).exists():
        strategies.append(MLPredictor(model_path=ml_model_path))
    return EnsembleVoter(strategies)


__all__ = [
    "AbstractStrategy",
    "Breakout",
    "Direction",
    "EnsembleDecision",
    "EnsembleVoter",
    "GridHint",
    "MLPredictor",
    "MeanReversion",
    "Signal",
    "SmartDCA",
    "TrendFollowing",
    "default_ensemble",
]
