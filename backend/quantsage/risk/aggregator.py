"""8-Layer risk aggregator.

Every order proposal flows through `evaluate()`. The first layer that rejects
short-circuits the pipeline, its reason is returned to the execution router,
and the event is logged for later audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from ..exceptions import RiskBlockedError
from ..features.regime import Regime
from ..strategies.base import Direction
from ..utils.logger import logger
from .black_swan import BlackSwanDetector
from .drawdown_guard import DrawdownGuard, DrawdownSnapshot
from .kill_switch import kill_switch
from .position_sizer import SizingResult, size_position


class Layer(StrEnum):
    REGIME = "1_REGIME"
    SIGNAL_QUALITY = "2_SIGNAL_QUALITY"
    CORRELATION = "3_CORRELATION"
    SIZING = "4_SIZING"
    BLACK_SWAN = "5_BLACK_SWAN"
    DRAWDOWN = "6_DRAWDOWN"
    LIQUIDITY = "7_LIQUIDITY"
    KILL_SWITCH = "8_KILL_SWITCH"


@dataclass
class OrderProposal:
    symbol: str
    direction: Direction
    confidence: float
    strategy: str
    regime: Regime
    reasoning: str


@dataclass
class RiskContext:
    equity_krw: Decimal
    day_start_equity: Decimal
    week_start_equity: Decimal
    equity_peak: Decimal
    existing_positions: dict[str, Decimal]  # symbol -> notional KRW
    correlation_map: dict[tuple[str, str], float]
    realized_vol_annual: float
    orderbook_depth_krw: Decimal
    allowed_strategies_by_regime: dict[Regime, set[str]]
    black_swan: BlackSwanDetector


@dataclass
class RiskDecision:
    allowed: bool
    blocked_layer: Layer | None
    reason: str
    sizing: SizingResult | None


class RiskAggregator:
    def __init__(self, min_confidence: float = 0.65) -> None:
        self.min_confidence = min_confidence
        self.drawdown_guard = DrawdownGuard()

    async def evaluate(
        self, proposal: OrderProposal, ctx: RiskContext
    ) -> RiskDecision:
        # Layer 8 first (fast check, no work if killed)
        if kill_switch.is_active:
            return self._deny(Layer.KILL_SWITCH, f"kill-switch: {kill_switch.message}")

        # Layer 1: regime → strategy gate
        allowed = ctx.allowed_strategies_by_regime.get(proposal.regime, set())
        if allowed and proposal.strategy not in allowed:
            return self._deny(
                Layer.REGIME,
                f"{proposal.strategy} not allowed in {proposal.regime}",
            )

        # Layer 2: signal quality
        if proposal.confidence < self.min_confidence:
            return self._deny(
                Layer.SIGNAL_QUALITY,
                f"confidence {proposal.confidence:.2f} < {self.min_confidence:.2f}",
            )

        # Layer 3: correlation guard
        if proposal.direction == Direction.BUY:
            for held_symbol in ctx.existing_positions:
                if held_symbol == proposal.symbol:
                    continue
                corr = ctx.correlation_map.get(
                    (proposal.symbol, held_symbol)
                ) or ctx.correlation_map.get((held_symbol, proposal.symbol), 0.0)
                if corr > 0.75:
                    return self._deny(
                        Layer.CORRELATION,
                        f"corr({proposal.symbol}, {held_symbol})={corr:.2f} > 0.75",
                    )

        # Layer 4: position sizer
        existing = ctx.existing_positions.get(proposal.symbol, Decimal("0"))
        sizing = size_position(
            equity_krw=ctx.equity_krw,
            confidence=proposal.confidence,
            realized_vol_annual=ctx.realized_vol_annual,
            existing_notional_krw=existing,
        )
        if sizing.notional_krw <= 0:
            return self._deny(Layer.SIZING, f"sizer returned 0: {sizing.reason}")

        # Layer 5: black swan
        ok, why = await ctx.black_swan.check()
        if not ok:
            return self._deny(Layer.BLACK_SWAN, why)

        # Layer 6: drawdown
        snap = DrawdownSnapshot(
            equity_peak=ctx.equity_peak,
            equity_now=ctx.equity_krw,
            day_start_equity=ctx.day_start_equity,
            week_start_equity=ctx.week_start_equity,
            day=__import__("datetime").date.today(),
        )
        ok, why = await self.drawdown_guard.check(snap)
        if not ok:
            return self._deny(Layer.DRAWDOWN, why)

        # Layer 7: liquidity (order vs 10% of visible depth)
        if ctx.orderbook_depth_krw > 0 and sizing.notional_krw > ctx.orderbook_depth_krw * Decimal("0.1"):
            # Down-size instead of deny
            adjusted = ctx.orderbook_depth_krw * Decimal("0.1")
            sizing = SizingResult(
                adjusted,
                f"liquidity slice: {adjusted} (was {sizing.notional_krw}). {sizing.reason}",
            )

        return RiskDecision(
            allowed=True,
            blocked_layer=None,
            reason=f"passed all layers. {sizing.reason}",
            sizing=sizing,
        )

    @staticmethod
    def _deny(layer: Layer, reason: str) -> RiskDecision:
        logger.warning(f"Risk blocked at {layer}: {reason}")
        return RiskDecision(allowed=False, blocked_layer=layer, reason=reason, sizing=None)

    def evaluate_or_raise(self, decision: RiskDecision) -> None:
        if not decision.allowed:
            raise RiskBlockedError(
                layer=str(decision.blocked_layer),
                reason=decision.reason,
            )
