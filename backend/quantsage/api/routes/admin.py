"""Kill-switch + loop control."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ...risk.kill_switch import KillReason, kill_switch
from ..deps import current_user
from .orchestrator_state import get_main_loop

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/kill")
async def kill(user: Annotated[str, Depends(current_user)], reason: str = "manual from dashboard") -> dict:
    await kill_switch.trigger(KillReason.MANUAL, reason)
    loop = get_main_loop()
    loop.stop()
    return {"status": "killed", "reason": reason, "by": user}


@router.post("/reset")
async def reset(user: Annotated[str, Depends(current_user)]) -> dict:
    await kill_switch.reset()
    return {"status": "reset", "by": user}


@router.get("/status")
async def status(user: Annotated[str, Depends(current_user)]) -> dict:
    loop = get_main_loop()
    return {
        "loop": {
            "running": loop.state.running,
            "iterations": loop.state.iterations,
            "last_regime": str(loop.state.last_regime) if loop.state.last_regime else None,
            "last_error": loop.state.last_error,
            "symbols": loop.symbols,
        },
        "kill_switch": {
            "active": kill_switch.is_active,
            "reason": str(kill_switch.reason) if kill_switch.reason else None,
            "message": kill_switch.message,
        },
    }
