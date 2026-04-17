"""Upbit adapter (REST + WebSocket).

JWT signing per request; rate-limited with aiolimiter. WebSocket auto-reconnects
with exponential back-off. Minimum order value (5000 KRW) is enforced here so the
rest of the stack doesn't need to care.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from decimal import Decimal
from typing import AsyncIterator
from urllib.parse import urlencode

import httpx
import jwt
import websockets
from aiolimiter import AsyncLimiter

from ..config import settings
from ..exceptions import (
    ExchangeError,
    InsufficientFundsError,
    OrderRejectedError,
    RateLimitError,
)
from ..utils.logger import logger
from .base import (
    AbstractExchange,
    Balance,
    Candle,
    Order,
    OrderSide,
    OrderType,
    Ticker,
)

UPBIT_REST = "https://api.upbit.com"
UPBIT_WS = "wss://api.upbit.com/websocket/v1"
MIN_ORDER_KRW = Decimal("5000")


class UpbitExchange(AbstractExchange):
    name = "upbit"

    def __init__(self, access_key: str | None = None, secret_key: str | None = None):
        self.access_key = access_key or settings.upbit_access_key
        self.secret_key = secret_key or settings.upbit_secret_key
        # Upbit: 주문 초당 8회, 공개 초당 30회
        self._order_limiter = AsyncLimiter(max_rate=8, time_period=1)
        self._public_limiter = AsyncLimiter(max_rate=30, time_period=1)
        self._client = httpx.AsyncClient(timeout=10.0)

    # ----- internal -----

    def _jwt_headers(self, query: dict | None = None) -> dict[str, str]:
        payload: dict = {
            "access_key": self.access_key,
            "nonce": str(uuid.uuid4()),
        }
        if query:
            qs = urlencode(query, doseq=True).encode()
            payload["query_hash"] = hashlib.sha512(qs).hexdigest()
            payload["query_hash_alg"] = "SHA512"
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    async def _get(self, path: str, params: dict | None = None, auth: bool = False) -> dict:
        async with self._public_limiter:
            headers = self._jwt_headers(params) if auth else {}
            r = await self._client.get(f"{UPBIT_REST}{path}", params=params, headers=headers)
        if r.status_code == 429:
            raise RateLimitError(f"Upbit 429 on {path}")
        if r.status_code >= 400:
            raise ExchangeError(f"Upbit GET {path} -> {r.status_code}: {r.text}")
        return r.json()

    async def _post(self, path: str, body: dict) -> dict:
        async with self._order_limiter:
            headers = {**self._jwt_headers(body), "Content-Type": "application/json"}
            r = await self._client.post(f"{UPBIT_REST}{path}", json=body, headers=headers)
        if r.status_code == 429:
            raise RateLimitError(f"Upbit 429 on {path}")
        if r.status_code >= 400:
            detail = r.text
            if "insufficient" in detail.lower():
                raise InsufficientFundsError(detail)
            raise OrderRejectedError(f"Upbit POST {path} -> {r.status_code}: {detail}")
        return r.json()

    async def _delete(self, path: str, params: dict) -> dict:
        async with self._order_limiter:
            headers = self._jwt_headers(params)
            r = await self._client.delete(
                f"{UPBIT_REST}{path}", params=params, headers=headers
            )
        if r.status_code >= 400:
            raise ExchangeError(f"Upbit DELETE {path} -> {r.status_code}: {r.text}")
        return r.json()

    # ----- public -----

    async def fetch_markets(self) -> list[dict]:
        return await self._get("/v1/market/all?isDetails=false")

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1m", limit: int = 200
    ) -> list[Candle]:
        tf_map = {
            "1m": ("/v1/candles/minutes/1", {}),
            "5m": ("/v1/candles/minutes/5", {}),
            "15m": ("/v1/candles/minutes/15", {}),
            "1h": ("/v1/candles/minutes/60", {}),
            "4h": ("/v1/candles/minutes/240", {}),
            "1d": ("/v1/candles/days", {}),
            "1w": ("/v1/candles/weeks", {}),
        }
        if timeframe not in tf_map:
            raise ExchangeError(f"Unsupported timeframe: {timeframe}")
        path, base_params = tf_map[timeframe]
        params = {"market": symbol, "count": min(limit, 200), **base_params}
        raw = await self._get(path, params)
        out: list[Candle] = []
        for row in reversed(raw):
            out.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=int(row["timestamp"]),
                    open=Decimal(str(row["opening_price"])),
                    high=Decimal(str(row["high_price"])),
                    low=Decimal(str(row["low_price"])),
                    close=Decimal(str(row["trade_price"])),
                    volume=Decimal(str(row["candle_acc_trade_volume"])),
                )
            )
        return out

    async def fetch_ticker(self, symbol: str) -> Ticker:
        rows = await self._get("/v1/ticker", {"markets": symbol})
        row = rows[0]
        price = Decimal(str(row["trade_price"]))
        return Ticker(
            symbol=symbol,
            bid=price,  # /v1/ticker does not expose bid/ask; orderbook call does
            ask=price,
            last=price,
            timestamp=int(row["timestamp"]),
        )

    async def fetch_orderbook(self, symbol: str, depth: int = 10) -> dict:
        rows = await self._get("/v1/orderbook", {"markets": symbol})
        ob = rows[0]
        units = ob["orderbook_units"][:depth]
        return {
            "symbol": symbol,
            "bids": [(u["bid_price"], u["bid_size"]) for u in units],
            "asks": [(u["ask_price"], u["ask_size"]) for u in units],
            "timestamp": ob["timestamp"],
        }

    # ----- private -----

    async def fetch_balance(self) -> dict[str, Balance]:
        if not self.access_key:
            raise ExchangeError("Upbit API key missing")
        rows = await self._get("/v1/accounts", auth=True)
        out: dict[str, Balance] = {}
        for row in rows:
            asset = row["currency"]
            out[asset] = Balance(
                asset=asset,
                free=Decimal(str(row["balance"])),
                locked=Decimal(str(row["locked"])),
            )
        return out

    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        amount: Decimal,
        price: Decimal | None = None,
    ) -> Order:
        if settings.trading_mode != "live" or not settings.enable_live_trading:
            raise ExchangeError(
                "Live trading disabled. Set TRADING_MODE=live and ENABLE_LIVE_TRADING=true"
            )
        body: dict = {"market": symbol, "side": "bid" if side == "buy" else "ask"}
        if order_type == "limit":
            if price is None:
                raise OrderRejectedError("Limit order requires price")
            body["ord_type"] = "limit"
            body["price"] = str(price)
            body["volume"] = str(amount)
            if price * amount < MIN_ORDER_KRW:
                raise OrderRejectedError(
                    f"Order value below Upbit minimum {MIN_ORDER_KRW} KRW"
                )
        elif order_type == "market":
            if side == "buy":
                body["ord_type"] = "price"
                body["price"] = str(amount)  # KRW amount for market buy
                if amount < MIN_ORDER_KRW:
                    raise OrderRejectedError(
                        f"Market buy value below {MIN_ORDER_KRW} KRW"
                    )
            else:
                body["ord_type"] = "market"
                body["volume"] = str(amount)
        logger.info(f"Upbit ORDER {symbol} {side} {order_type} amount={amount} price={price}")
        data = await self._post("/v1/orders", body)
        return self._map_order(data)

    async def cancel_order(self, order_id: str) -> bool:
        await self._delete("/v1/order", {"uuid": order_id})
        return True

    async def fetch_open_orders(self, symbol: str | None = None) -> list[Order]:
        params: dict = {"state": "wait"}
        if symbol:
            params["market"] = symbol
        rows = await self._get("/v1/orders", params, auth=True)
        return [self._map_order(r) for r in rows]

    @staticmethod
    def _map_order(row: dict) -> Order:
        return Order(
            id=row.get("uuid", ""),
            symbol=row.get("market", ""),
            side="buy" if row.get("side") == "bid" else "sell",
            type="limit" if row.get("ord_type") == "limit" else "market",
            price=Decimal(str(row["price"])) if row.get("price") else None,
            amount=Decimal(str(row.get("volume", "0"))),
            filled=Decimal(str(row.get("executed_volume", "0"))),
            status=row.get("state", "unknown"),
            timestamp=int(time.time() * 1000),
        )

    # ----- websocket -----

    async def stream_ticker(self, symbols: list[str]) -> AsyncIterator[Ticker]:
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(UPBIT_WS, ping_interval=30) as ws:
                    sub = [
                        {"ticket": str(uuid.uuid4())},
                        {"type": "ticker", "codes": symbols},
                        {"format": "DEFAULT"},
                    ]
                    await ws.send(json.dumps(sub))
                    backoff = 1.0
                    async for raw in ws:
                        data = json.loads(raw)
                        yield Ticker(
                            symbol=data["code"],
                            bid=Decimal(str(data.get("trade_price", 0))),
                            ask=Decimal(str(data.get("trade_price", 0))),
                            last=Decimal(str(data.get("trade_price", 0))),
                            timestamp=int(data.get("timestamp", time.time() * 1000)),
                        )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Upbit WS disconnected: {exc}. Retry in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def close(self) -> None:
        await self._client.aclose()
