"""Live strategy signal inspection.

Given a symbol, fetch recent OHLCV and return what each strategy thinks right
now, plus the ensemble decision. Prefers DB (deeper history when seeded) and
falls back to a fresh Upbit REST call otherwise.
"""

from __future__ import annotations

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from ...exchanges import create_exchange
from ...features.regime import detect_regime
from ...market_data.storage import load_ohlcv
from ...orchestrator.main_loop import candles_to_df
from ...strategies import default_ensemble
from ..deps import current_user

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/signals/{symbol}")
async def signals(
    symbol: str, user: Annotated[str, Depends(current_user)], timeframe: str = "1h"
) -> dict:
    # Prefer seeded DB (deeper history = valid regime / EMA200)
    try:
        rows = await load_ohlcv("upbit", symbol, timeframe, 1500)
    except Exception:
        rows = []
    if rows and len(rows) >= 210:
        df = pd.DataFrame(rows)
    else:
        exchange = create_exchange("upbit")
        try:
            candles = await exchange.fetch_ohlcv(symbol, timeframe, 200)
        finally:
            await exchange.close()
        if len(candles) < 200:
            raise HTTPException(400, f"insufficient history ({len(candles)})")
        df = candles_to_df(candles)
    regime = detect_regime(df)
    ensemble = default_ensemble()
    decision = ensemble.decide(df, regime)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "regime": str(regime),
        "ensemble": {
            "direction": str(decision.direction),
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
        },
        "votes": [
            {
                "strategy": name,
                "direction": str(s.direction),
                "confidence": s.confidence,
                "reasoning": s.reasoning,
            }
            for name, s in decision.votes.items()
        ],
    }
