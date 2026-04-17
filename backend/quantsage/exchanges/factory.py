"""Exchange factory.

Keep strategies exchange-agnostic: `create_exchange("upbit")` in strategies,
not `UpbitExchange(...)` directly.
"""

from __future__ import annotations

from .base import AbstractExchange
from .upbit import UpbitExchange


def create_exchange(name: str) -> AbstractExchange:
    name = name.lower()
    if name == "upbit":
        return UpbitExchange()
    raise ValueError(f"Unknown exchange: {name}")
