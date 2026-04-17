"""Paper account state + equity."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends

from ..deps import current_user
from .orchestrator_state import get_paper_executor

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
async def list_positions(user: Annotated[str, Depends(current_user)]) -> dict:
    paper = get_paper_executor()
    return {
        "cash_krw": str(paper.account.cash_krw),
        "positions": [
            {
                "symbol": sym,
                "amount": str(qty),
                "avg_entry": str(paper.account.avg_entry.get(sym, Decimal("0"))),
            }
            for sym, qty in paper.account.positions.items()
            if qty > 0
        ],
        "trade_log_tail": paper.account.trade_log[-20:],
    }


@router.get("/equity")
async def equity(user: Annotated[str, Depends(current_user)]) -> dict:
    paper = get_paper_executor()
    # No live marks here; caller passes marks separately in production.
    return {
        "cash_krw": str(paper.account.cash_krw),
        "n_open_positions": sum(1 for q in paper.account.positions.values() if q > 0),
    }
