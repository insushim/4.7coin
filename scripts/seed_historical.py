"""Seed historical OHLCV from Upbit into Postgres.

Uses Upbit's `to` cursor to paginate backwards. Safe to re-run — UPSERT dedup.

Usage:
    python scripts/seed_historical.py --symbols KRW-BTC,KRW-ETH --timeframe 1h --days 365
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from quantsage.exchanges import UpbitExchange  # noqa: E402
from quantsage.market_data.storage import bulk_insert_ohlcv, candle_to_row  # noqa: E402
from quantsage.utils.logger import logger, setup_logger  # noqa: E402

_BARS_PER_DAY = {
    "1m": 1440, "5m": 288, "15m": 96, "1h": 24,
    "4h": 6, "1d": 1, "1w": 1 / 7,
}


async def seed_symbol(
    exchange: UpbitExchange, symbol: str, timeframe: str, days: int
) -> int:
    total_bars = int(days * _BARS_PER_DAY[timeframe])
    cursor: str | None = None
    total = 0
    calls = 0
    while total < total_bars:
        remaining = total_bars - total
        batch_size = min(200, remaining)
        try:
            candles = await exchange.fetch_ohlcv(symbol, timeframe, batch_size, to=cursor)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"{symbol}: fetch error at cursor={cursor} — {exc}")
            break
        if not candles:
            break
        rows = [candle_to_row("upbit", symbol, timeframe, c) for c in candles]
        n = await bulk_insert_ohlcv(rows)
        total += n
        calls += 1
        # next cursor = oldest timestamp in this batch
        oldest_ms = min(c.timestamp for c in candles)
        cursor = datetime.fromtimestamp(oldest_ms / 1000, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info(f"{symbol} {timeframe}: +{n} (total {total}/{total_bars}) cursor={cursor}")
        await asyncio.sleep(0.1)
    return total


async def seed(symbols: list[str], timeframe: str, days: int) -> None:
    setup_logger()
    exchange = UpbitExchange()
    try:
        for sym in symbols:
            logger.info(f"=== seeding {sym} {timeframe} for {days}d ===")
            n = await seed_symbol(exchange, sym, timeframe, days)
            logger.info(f"{sym}: done ({n} rows)")
    finally:
        await exchange.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="KRW-BTC,KRW-ETH")
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--days", type=int, default=365)
    args = ap.parse_args()
    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    asyncio.run(seed(syms, args.timeframe, args.days))


if __name__ == "__main__":
    main()
