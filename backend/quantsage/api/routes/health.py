"""Health + diagnostics."""

from __future__ import annotations

from fastapi import APIRouter

from ...config import settings
from ...risk.kill_switch import kill_switch

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "trading_mode": settings.trading_mode,
        "live_enabled": settings.enable_live_trading,
        "kill_switch": {
            "active": kill_switch.is_active,
            "reason": str(kill_switch.reason) if kill_switch.reason else None,
            "message": kill_switch.message,
        },
    }


@router.get("/version")
async def version() -> dict:
    from ... import __version__

    return {"version": __version__}
