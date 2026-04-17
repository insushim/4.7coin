"""Position sizing: Kelly/4 × Volatility-Target × Equity, hard-clamped.

The sizer is deliberately conservative: full-Kelly has blown accounts; fractional
Kelly with a vol-target cap is the industry standard (Lopez de Prado,
Bouchaud).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..config import settings


@dataclass(frozen=True)
class SizingResult:
    notional_krw: Decimal
    reason: str


def kelly_fraction(win_rate: float, payoff_ratio: float, fraction: float = 0.25) -> float:
    """Fractional Kelly.

    win_rate: historical p(win)
    payoff_ratio: avg_win / avg_loss
    fraction: Kelly damping (default 1/4)
    """
    if payoff_ratio <= 0:
        return 0.0
    kelly = win_rate - (1 - win_rate) / payoff_ratio
    return max(0.0, kelly * fraction)


def volatility_target_fraction(
    realized_vol_annual: float, target_vol_annual: float | None = None
) -> float:
    target = target_vol_annual or settings.vol_target_annual
    if realized_vol_annual <= 0:
        return 0.0
    return min(1.0, target / realized_vol_annual)


def size_position(
    *,
    equity_krw: Decimal,
    confidence: float,
    win_rate: float = 0.52,
    payoff_ratio: float = 1.5,
    realized_vol_annual: float = 0.5,
    existing_notional_krw: Decimal = Decimal("0"),
) -> SizingResult:
    """Combined sizer.

    Returns KRW notional to add. Enforces:
      - per_trade_risk_pct hard cap
      - max_position_pct hard cap (considers existing exposure)
      - Kelly/4 × vol-target × confidence dampening
    """
    if equity_krw <= 0:
        return SizingResult(Decimal("0"), "equity <= 0")

    k = kelly_fraction(win_rate, payoff_ratio, settings.kelly_fraction)
    v = volatility_target_fraction(realized_vol_annual)
    combined = k * v * max(0.0, min(confidence, 1.0))

    # Per-trade absolute cap
    per_trade_cap = settings.per_trade_risk_pct
    frac = min(combined, per_trade_cap)

    proposed = equity_krw * Decimal(str(frac))

    # Position cap (cumulative)
    max_total = equity_krw * Decimal(str(settings.max_position_pct))
    headroom = max(Decimal("0"), max_total - existing_notional_krw)
    final = min(proposed, headroom)

    return SizingResult(
        final,
        f"kelly/4={k:.4f}, vol_target={v:.2f}, conf={confidence:.2f}, "
        f"combined_frac={frac:.4f}, headroom_krw={headroom}",
    )
