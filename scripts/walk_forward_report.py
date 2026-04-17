"""Full walk-forward out-of-sample test + HTML report.

Usage (DB-backed, recommended after seed_historical.py):
    python scripts/walk_forward_report.py --symbol KRW-BTC --timeframe 1h \
        --train 1500 --test 300 --step 300

Usage (live exchange, small sample only — Upbit single call ≤ 200 bars):
    python scripts/walk_forward_report.py --symbol KRW-BTC --timeframe 1h --live-fallback
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pandas as pd

from quantsage.backtest.report import run_walk_forward, save_report  # noqa: E402
from quantsage.strategies import default_ensemble  # noqa: E402
from quantsage.utils.logger import logger, setup_logger  # noqa: E402


async def _load_from_db(symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
    from quantsage.market_data.storage import load_ohlcv

    rows = await load_ohlcv("upbit", symbol, timeframe, bars)
    return pd.DataFrame(rows)


async def _load_from_exchange(symbol: str, timeframe: str) -> pd.DataFrame:
    from quantsage.exchanges import UpbitExchange
    from quantsage.orchestrator.main_loop import candles_to_df

    ex = UpbitExchange()
    try:
        candles = await ex.fetch_ohlcv(symbol, timeframe, 200)
        return candles_to_df(candles)
    finally:
        await ex.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="KRW-BTC")
    ap.add_argument("--timeframe", default="1h")
    ap.add_argument("--train", type=int, default=1200)
    ap.add_argument("--test", type=int, default=300)
    ap.add_argument("--step", type=int, default=300)
    ap.add_argument("--max-bars", type=int, default=20000)
    ap.add_argument("--live-fallback", action="store_true",
                    help="fetch from Upbit if DB empty (max 200 bars → single window)")
    args = ap.parse_args()
    setup_logger()

    df = asyncio.run(_load_from_db(args.symbol, args.timeframe, args.max_bars))
    if df.empty:
        if args.live_fallback:
            logger.warning("DB empty — falling back to live fetch (200 bars)")
            df = asyncio.run(_load_from_exchange(args.symbol, args.timeframe))
        else:
            raise SystemExit(
                "DB has no OHLCV. Run scripts/seed_historical.py first, "
                "or re-run with --live-fallback."
            )
    logger.info(f"Loaded {len(df)} bars for {args.symbol} {args.timeframe}")

    if len(df) < args.train + args.test:
        raise SystemExit(
            f"Not enough bars ({len(df)}) for train={args.train}+test={args.test}. "
            f"Seed more history."
        )

    ensemble = default_ensemble()
    windows, aggregate = run_walk_forward(
        df,
        ensemble,
        train_bars=args.train,
        test_bars=args.test,
        step_bars=args.step,
    )
    html_path = save_report(
        windows, aggregate, symbol=args.symbol, timeframe=args.timeframe
    )
    logger.info(f"Walk-forward report written to {html_path}")
    print(f"✅ {html_path}")
    print(
        f"Aggregate: Sharpe={aggregate.sharpe:.2f}, "
        f"Return={aggregate.total_return:.2%}, "
        f"MDD={aggregate.max_drawdown:.2%}, "
        f"DSR={aggregate.deflated_sharpe:.3f}, "
        f"Trades={aggregate.n_trades}"
    )


if __name__ == "__main__":
    main()
