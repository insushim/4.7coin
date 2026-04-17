"""Black-swan / flash-crash detector.

Monitors rolling 5-minute returns. If a single 5m return breaches
`circuit_breaker_5m_pct` (default -5%), new entries are blocked and the
kill-switch fires to flatten exposure.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal

from ..config import settings
from .kill_switch import KillReason, kill_switch


@dataclass
class PricePoint:
    timestamp: int  # seconds
    price: Decimal


class BlackSwanDetector:
    def __init__(self, window_seconds: int = 300) -> None:
        self.window = window_seconds
        self._points: deque[PricePoint] = deque()

    def add(self, timestamp: int, price: Decimal) -> None:
        self._points.append(PricePoint(timestamp, price))
        cutoff = timestamp - self.window
        while self._points and self._points[0].timestamp < cutoff:
            self._points.popleft()

    def max_drawdown_in_window(self) -> float:
        if len(self._points) < 2:
            return 0.0
        prices = [float(p.price) for p in self._points]
        peak = prices[0]
        worst = 0.0
        for p in prices:
            peak = max(peak, p)
            dd = (p - peak) / peak if peak else 0.0
            worst = min(worst, dd)
        return worst

    async def check(self) -> tuple[bool, str]:
        worst = self.max_drawdown_in_window()
        threshold = settings.circuit_breaker_5m_pct
        if worst <= threshold:
            await kill_switch.trigger(
                KillReason.BLACK_SWAN,
                f"5-min drawdown {worst:.2%} breached {threshold:.0%}.",
            )
            return False, f"flash crash: {worst:.2%}"
        return True, "ok"
