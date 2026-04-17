"""Seed historical OHLCV from Upbit into Postgres (optional TimescaleDB).

Usage:
    python scripts/seed_historical.py --symbols KRW-BTC,KRW-ETH --days 365
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from quantsage.exchanges import UpbitExchange  # noqa: E402
from quantsage.market_data.storage import bulk_insert_ohlcv, candle_to_row  # noqa: E402
from quantsage.utils.logger import logger, setup_logger  # noqa: E402


async def seed(symbols: list[str], timeframe: str, days: int) -> None:
    setup_logger()
    exchange = UpbitExchange()
    try:
        for sym in symbols:
            logger.info(f"Seeding {sym} {timeframe} for {days}d")
            # Upbit single call max 200 candles; for 1h × 365d = 8760 bars → ~44 calls
            bars_per_day = {"1m": 1440, "5m": 288, "15m": 96, "1h": 24, "4h": 6, "1d": 1}[
                timeframe
            ]
            total = days * bars_per_day
            inserted = 0
            # Simple strategy: fetch last N, paginate via `to` in future revision
            chunks = (total + 199) // 200
            for _ in range(min(chunks, 50)):  # cap 10k bars per symbol this pass
                candles = await exchange.fetch_ohlcv(sym, timeframe, 200)
                rows = [candle_to_row("upbit", sym, timeframe, c) for c in candles]
                inserted += await bulk_insert_ohlcv(rows)
                await asyncio.sleep(0.1)
            logger.info(f"{sym}: upserted {inserted} rows")
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
