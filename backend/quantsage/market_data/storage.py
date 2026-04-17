"""Bulk OHLCV insert into TimescaleDB."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from ..db.models import Ohlcv
from ..db.session import get_session


async def bulk_insert_ohlcv(rows: list[dict]) -> int:
    """UPSERT on (time, exchange, symbol, timeframe)."""
    if not rows:
        return 0
    async with get_session() as s:
        stmt = insert(Ohlcv).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["time", "exchange", "symbol", "timeframe"]
        )
        await s.execute(stmt)
    return len(rows)


def candle_to_row(exchange: str, symbol: str, timeframe: str, candle) -> dict:
    return {
        "time": datetime.fromtimestamp(candle.timestamp / 1000, tz=timezone.utc),
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
    }


async def load_ohlcv(
    exchange: str, symbol: str, timeframe: str, limit: int = 500
) -> list[dict]:
    async with get_session() as s:
        q = (
            select(Ohlcv)
            .where(
                Ohlcv.exchange == exchange,
                Ohlcv.symbol == symbol,
                Ohlcv.timeframe == timeframe,
            )
            .order_by(Ohlcv.time.desc())
            .limit(limit)
        )
        rows = (await s.execute(q)).scalars().all()
    rows = list(reversed(rows))
    return [
        {
            "timestamp": int(r.time.timestamp() * 1000),
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": float(r.volume),
        }
        for r in rows
    ]


async def purge_old(exchange: str, symbol: str, timeframe: str, before: datetime) -> int:
    async with get_session() as s:
        stmt = delete(Ohlcv).where(
            Ohlcv.exchange == exchange,
            Ohlcv.symbol == symbol,
            Ohlcv.timeframe == timeframe,
            Ohlcv.time < before,
        )
        res = await s.execute(stmt)
    return res.rowcount or 0
