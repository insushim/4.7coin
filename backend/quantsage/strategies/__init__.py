from .base import AbstractStrategy, Direction, Signal
from .breakout import Breakout
from .dca_smart import SmartDCA
from .ensemble_voter import EnsembleDecision, EnsembleVoter
from .grid import GridHint
from .mean_reversion import MeanReversion
from .trend_following import TrendFollowing


def default_ensemble() -> EnsembleVoter:
    return EnsembleVoter(
        [TrendFollowing(), MeanReversion(), Breakout(), GridHint(), SmartDCA()]
    )


__all__ = [
    "AbstractStrategy",
    "Breakout",
    "Direction",
    "EnsembleDecision",
    "EnsembleVoter",
    "GridHint",
    "MeanReversion",
    "Signal",
    "SmartDCA",
    "TrendFollowing",
    "default_ensemble",
]
