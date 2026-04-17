"""Run backtests on demand."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ...backtest import BacktestEngine, EngineConfig
from ...exchanges import create_exchange
from ...orchestrator.main_loop import candles_to_df
from ...strategies import default_ensemble
from ..deps import current_user

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run")
async def run_backtest(
    user: Annotated[str, Depends(current_user)],
    symbol: str = "KRW-BTC",
    timeframe: str = "1h",
    bars: int = 1500,
    initial_equity: float = 10_000_000,
) -> dict:
    exchange = create_exchange("upbit")
    try:
        # Upbit single-call limit is 200; stitch multiple calls
        collected = []
        remaining = bars
        last = None  # pagination via 'to' not wired here → take what fits
        per = min(200, remaining)
        collected = await exchange.fetch_ohlcv(symbol, timeframe, per)
        if len(collected) < 210:
            raise HTTPException(400, f"insufficient history ({len(collected)})")
    finally:
        await exchange.close()

    df = candles_to_df(collected)
    engine = BacktestEngine(default_ensemble(), engine_config=EngineConfig(initial_equity=initial_equity))
    result, metrics = engine.run(df, symbol=symbol)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": len(df),
        "initial_equity": result.initial_equity,
        "final_equity": result.final_equity,
        "total_return": result.total_return,
        "metrics": {
            "sharpe": metrics.sharpe,
            "sortino": metrics.sortino,
            "max_drawdown": metrics.max_drawdown,
            "calmar": metrics.calmar,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "deflated_sharpe": metrics.deflated_sharpe,
            "n_trades": metrics.n_trades,
        },
        "equity_curve_tail": [
            {"i": i, "equity": v}
            for i, v in list(zip(result.equity_curve.index[-50:], result.equity_curve.values[-50:]))
        ],
        "trades": [
            {
                "entry_ts": t.entry_ts,
                "exit_ts": t.exit_ts,
                "direction": str(t.direction),
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "reason_entry": t.reason_entry,
                "reason_exit": t.reason_exit,
            }
            for t in result.trades[-50:]
        ],
    }
