"""Process-wide kill-switch.

When engaged, all new orders are rejected and the orchestrator halts on the next
tick. Activation is manual (Telegram /kill, dashboard button) or automatic
(drawdown guard, black-swan detector, WS-loss timer).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum


class KillReason(StrEnum):
    MANUAL = "MANUAL"
    DAILY_LOSS = "DAILY_LOSS"
    WEEKLY_LOSS = "WEEKLY_LOSS"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    BLACK_SWAN = "BLACK_SWAN"
    WS_DEAD = "WS_DEAD"
    EXCHANGE_DOWN = "EXCHANGE_DOWN"


@dataclass
class KillState:
    active: bool = False
    reason: KillReason | None = None
    triggered_at: float | None = None
    message: str = ""
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class KillSwitch:
    def __init__(self) -> None:
        self._state = KillState()

    @property
    def is_active(self) -> bool:
        return self._state.active

    @property
    def reason(self) -> KillReason | None:
        return self._state.reason

    @property
    def message(self) -> str:
        return self._state.message

    async def trigger(self, reason: KillReason, message: str = "") -> None:
        async with self._state.lock:
            if self._state.active:
                return
            import time

            self._state.active = True
            self._state.reason = reason
            self._state.triggered_at = time.time()
            self._state.message = message

    async def reset(self) -> None:
        async with self._state.lock:
            self._state.active = False
            self._state.reason = None
            self._state.triggered_at = None
            self._state.message = ""


kill_switch = KillSwitch()
