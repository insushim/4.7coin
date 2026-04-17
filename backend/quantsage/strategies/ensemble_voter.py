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
        signals: dict[str, Signal] = {s.name: s.generate_signal(df, regime) for s in self.strategies}
        buys = [s for s in signals.values() if s.direction == Direction.BUY]
        sells = [s for s in signals.values() if s.direction == Direction.SELL]

        total = len(self.strategies)
        threshold_majority = total // 2 + 1

        if len(buys) >= threshold_majority and len(buys) > len(sells):
            winning = buys
            losing = sells
            direction = Direction.BUY
        elif len(sells) >= threshold_majority and len(sells) > len(buys):
            winning = sells
            losing = buys
            direction = Direction.SELL
        else:
            return EnsembleDecision(
                Direction.HOLD,
                0.0,
                signals,
                f"No majority: BUY={len(buys)}, SELL={len(sells)}, HOLD={total - len(buys) - len(sells)}",
            )

        conf = sum(s.confidence for s in winning) / len(winning)
        if losing:  # opposing signals → raise bar
            bar = max(self.min_confidence, 0.75)
        else:
            bar = self.min_confidence

        if conf < bar:
            return EnsembleDecision(
                Direction.HOLD,
                conf,
                signals,
                f"confidence {conf:.2f} < threshold {bar:.2f}",
            )

        return EnsembleDecision(
            direction,
            conf,
            signals,
            f"{direction} majority {len(winning)}/{total}, conf={conf:.2f}",
        )
