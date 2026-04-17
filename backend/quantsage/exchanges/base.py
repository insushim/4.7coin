"""Exchange abstraction.

Every exchange adapter must expose the same surface so strategies and the
execution router stay portable. All errors are translated to
`quantsage.exceptions` types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

OrderSide = Literal["buy", "sell"]
OrderType = Literal["limit", "market"]


@dataclass(frozen=True)
class Ticker:
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    timestamp: int  # ms


@dataclass(frozen=True)
class Balance:
    asset: str
    free: Decimal
    locked: Decimal

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


@dataclass(frozen=True)
class Order:
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    price: Decimal | None
    amount: Decimal
    filled: Decimal
    status: str
    timestamp: int


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: int  # ms
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class AbstractExchange(ABC):
    name: str = "abstract"

    @abstractmethod
    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1m", limit: int = 200
    ) -> list[Candle]:
        ...

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Ticker: ...

    @abstractmethod
    async def fetch_orderbook(self, symbol: str, depth: int = 10) -> dict: ...

    @abstractmethod
    async def fetch_balance(self) -> dict[str, Balance]: ...

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        amount: Decimal,
        price: Decimal | None = None,
    ) -> Order: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]: ...

    @abstractmethod
    async def fetch_markets(self) -> list[dict]: ...

    @abstractmethod
    async def stream_ticker(self, symbols: list[str]) -> AsyncIterator[Ticker]: ...

    async def close(self) -> None:  # pragma: no cover
        return None
