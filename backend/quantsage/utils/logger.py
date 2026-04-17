"""Structured logging via loguru with secret masking."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from loguru import logger

_SECRET_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|access[_-]?key)(\s*[:=]\s*)([\"']?)([A-Za-z0-9_\-\.=/+]{8,})\3",
    re.IGNORECASE,
)


def _mask(record: dict) -> None:
    msg = record["message"]
    record["message"] = _SECRET_PATTERN.sub(r"\1\2\3***MASKED***\3", msg)


def setup_logger(log_dir: str | Path = "data/logs", level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[trace_id]}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        filter=lambda r: _mask(r) or True,
    )

    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    logger.add(
        path / "quantsage_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="gz",
        level=level,
        enqueue=True,
        filter=lambda r: _mask(r) or True,
    )

    logger.configure(extra={"trace_id": "-"})


__all__ = ["logger", "setup_logger"]
