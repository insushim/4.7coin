"""Live strategy signal inspection.

Given a symbol, fetch recent OHLCV and return what each strategy thinks right
now, plus the ensemble decision. Useful for the dashboard explainer panel.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ...exchanges import create_exchange
from ...features.regime import detect_regime
from ...orchestrator.main_loop import candles_to_df
from ...strategies import default_ensemble
from ..deps import current_user

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/signals/{symbol}")
async def signals(
    symbol: str, user: Annotated[str, Depends(current_user)], timeframe: str = "1h"
) -> dict:
    exchange = create_exchange("upbit")
    try:
        candles = await exchange.fetch_ohlcv(symbol, timeframe, 300)
    finally:
        await exchange.close()
    if len(candles) < 210:
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
