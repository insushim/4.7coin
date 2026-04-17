"""Drawdown guard.

Three tiers (CLAUDE.md-documented):
  - daily -3%   → block new entries today
  - weekly -8%  → pause all strategies, require manual review
  - cumulative -15% → kill-switch + flatten everything
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..config import settings
from .kill_switch import KillReason, kill_switch


@dataclass
class DrawdownSnapshot:
    equity_peak: Decimal
    equity_now: Decimal
    day_start_equity: Decimal
    week_start_equity: Decimal
    day: date

    @property
    def cumulative_dd(self) -> float:
        if self.equity_peak <= 0:
            return 0.0
        return float((self.equity_now - self.equity_peak) / self.equity_peak)

    @property
    def daily_pnl_pct(self) -> float:
        if self.day_start_equity <= 0:
            return 0.0
        return float((self.equity_now - self.day_start_equity) / self.day_start_equity)

    @property
    def weekly_pnl_pct(self) -> float:
        if self.week_start_equity <= 0:
            return 0.0
        return float((self.equity_now - self.week_start_equity) / self.week_start_equity)


class DrawdownGuard:
    """Evaluate the drawdown snapshot and engage protections."""

    async def check(self, snap: DrawdownSnapshot) -> tuple[bool, str]:
        if snap.cumulative_dd <= -settings.max_drawdown_pct:
            await kill_switch.trigger(
                KillReason.MAX_DRAWDOWN,
                f"Cumulative DD {snap.cumulative_dd:.2%} breached "
                f"{-settings.max_drawdown_pct:.0%}. All positions to flatten.",
            )
            return False, f"kill-switch: max drawdown {snap.cumulative_dd:.2%}"

        if snap.weekly_pnl_pct <= -settings.max_weekly_loss_pct:
            await kill_switch.trigger(
                KillReason.WEEKLY_LOSS,
                f"Weekly loss {snap.weekly_pnl_pct:.2%} <= "
                f"{-settings.max_weekly_loss_pct:.0%}. System paused.",
            )
            return False, f"kill-switch: weekly loss {snap.weekly_pnl_pct:.2%}"

        if snap.daily_pnl_pct <= -settings.max_daily_loss_pct:
            # Daily doesn't flatten, only blocks new entries.
            return False, f"daily loss limit {snap.daily_pnl_pct:.2%}"

        return True, "ok"
