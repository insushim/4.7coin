"""Majority-vote ensemble over independent strategies.

A trade is allowed only when the winning direction has >= majority support AND
weighted confidence exceeds `min_confidence`. When opposite signals exist, the
confidence bar is raised to filter conflict.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..config import settings
from ..features.regime import Regime
from .base import AbstractStrategy, Direction, Signal


@dataclass
class EnsembleDecision:
    direction: Direction
    confidence: float
    votes: dict[str, Signal]
    reasoning: str


class EnsembleVoter:
    def __init__(
        self,
        strategies: list[AbstractStrategy],
        min_confidence: float | None = None,
    ):
        if not strategies:
            raise ValueError("ensemble requires at least one strategy")
        self.strategies = strategies
        self.min_confidence = min_confidence or settings.min_confidence

    def decide(self, df: pd.DataFrame, regime: Regime) -> EnsembleDecision:
        """Vote among strategies that had an opinion (direction != HOLD).

        Counting against *all* N strategies punished specialists (e.g. the
        mean-reverter sleeps in BULL regimes by design, so it can never "vote
        yes" for a trend trade). We now tally BUY vs SELL among the
        non-abstainers and require:
          1) at least `min_voters` directional signals (default 2)
          2) winning side > losing side (strict)
          3) weighted confidence >= threshold (raised when there's dissent)
        """
        signals: dict[str, Signal] = {s.name: s.generate_signal(df, regime) for s in self.strategies}
        buys = [s for s in signals.values() if s.direction == Direction.BUY]
        sells = [s for s in signals.values() if s.direction == Direction.SELL]
        voters = len(buys) + len(sells)
        min_voters = 2

        if voters < min_voters:
            return EnsembleDecision(
                Direction.HOLD,
                0.0,
                signals,
                f"Only {voters} directional voter(s); need {min_voters}",
            )

        if len(buys) > len(sells):
            winning, losing, direction = buys, sells, Direction.BUY
        elif len(sells) > len(buys):
            winning, losing, direction = sells, buys, Direction.SELL
        else:
            return EnsembleDecision(
                Direction.HOLD,
                0.0,
                signals,
                f"Tie: BUY={len(buys)}, SELL={len(sells)}",
            )

        conf = sum(s.confidence for s in winning) / len(winning)
        # raise bar when any strategy disagreed
        bar = max(self.min_confidence, 0.75) if losing else self.min_confidence

        if conf < bar:
            return EnsembleDecision(
                Direction.HOLD,
                conf,
                signals,
                f"{direction} would win {len(winning)}-{len(losing)} but conf {conf:.2f} < {bar:.2f}",
            )

        return EnsembleDecision(
            direction,
            conf,
            signals,
            f"{direction} wins {len(winning)}-{len(losing)}, conf={conf:.2f}",
        )
