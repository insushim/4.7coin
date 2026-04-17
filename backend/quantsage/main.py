"""FastAPI entrypoint + lifespan-managed trading loop."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import admin, auth, backtest, health, positions, strategies
from .api.routes.orchestrator_state import get_main_loop
from .config import settings
from .db.session import init_db
from .utils.logger import logger, setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger(level="INFO" if settings.app_env == "production" else "DEBUG")
    logger.info(
        f"QuantSage starting: env={settings.app_env} mode={settings.trading_mode} live={settings.is_live}"
    )
    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"DB init skipped: {exc}")

    # Background paper loop (commented by default — turn on once .env ready).
    loop = get_main_loop()
    task: asyncio.Task | None = None
    if settings.app_env == "production":
        task = asyncio.create_task(loop.run(interval_seconds=3600))
        logger.info("Main trading loop started (1h cadence)")
    try:
        yield
    finally:
        loop.stop()
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("QuantSage stopped cleanly")


app = FastAPI(
    title="QuantSage",
    version="0.1.0",
    description="AI Crypto Trader — Risk-First, Explainable, Regime-Aware",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(positions.router)
app.include_router(strategies.router)
app.include_router(backtest.router)
app.include_router(admin.router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "QuantSage",
        "version": "0.1.0",
        "docs": "/docs",
        "trading_mode": settings.trading_mode,
    }
