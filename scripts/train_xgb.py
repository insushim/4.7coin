"""Train the XGBoost direction model on cached OHLCV.

Usage:
    python scripts/train_xgb.py --symbol KRW-BTC --timeframe 1h --bars 8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from quantsage.exchanges import UpbitExchange  # noqa: E402
from quantsage.features.engineering import FeatureConfig  # noqa: E402
from quantsage.models.xgb import XGBConfig, train_on_ohlcv  # noqa: E402
from quantsage.orchestrator.main_loop import candles_to_df  # noqa: E402
from quantsage.utils.logger import setup_logger  # noqa: E402


async def collect(symbol: str, timeframe: str, bars: int):
    exchange = UpbitExchange()
    try:
        # single call ≤200; iterate with `to` not wired → stitch forward
        candles = await exchange.fetch_ohlcv(symbol, timeframe, min(bars, 200))
    finally:
        await exchange.close()
    return candles


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="KRW-BTC")
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--bars", type=int, default=4000)
    ap.add_argument("--out", default="data/models/xgb.json")
    ap.add_argument("--use-db", action="store_true",
                    help="read OHLCV from Postgres (seeded via scripts/seed_historical.py)")
    args = ap.parse_args()
    setup_logger()

    if args.use_db:
        from quantsage.market_data.storage import load_ohlcv

        rows = asyncio.run(load_ohlcv("upbit", args.symbol, args.timeframe, args.bars))
        if not rows:
            raise SystemExit("no OHLCV in DB — run seed_historical.py first")
        import pandas as pd

        df = pd.DataFrame(rows)
    else:
        candles = asyncio.run(collect(args.symbol, args.timeframe, args.bars))
        df = candles_to_df(candles)

    print(f"Loaded {len(df)} bars. Training XGBoost...")
    model, report = train_on_ohlcv(df, FeatureConfig(), XGBConfig())
    out = Path(args.out)
    model.save(out)
    (out.parent / f"{out.stem}_report.json").write_text(
        json.dumps(
            {**report, "importance_top20": [(f, float(v)) for f, v in report.get("importance_top20", [])]},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"Saved model to {out}")
    print(f"Top features: {report.get('importance_top20', [])[:5]}")


if __name__ == "__main__":
    main()
