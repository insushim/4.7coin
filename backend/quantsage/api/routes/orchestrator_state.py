"""Process-level singletons for the orchestrator + paper executor.

Kept here so routes can import without creating cycles.
"""

from __future__ import annotations

from ...execution.dry_run import PaperExecutor
from ...orchestrator.main_loop import MainLoop

_paper: PaperExecutor | None = None
_loop: MainLoop | None = None


def get_paper_executor() -> PaperExecutor:
    global _paper
    if _paper is None:
        _paper = PaperExecutor()
    return _paper


def get_main_loop() -> MainLoop:
    global _loop
    if _loop is None:
        _loop = MainLoop(
            symbols=["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP"],
            paper=get_paper_executor(),
        )
    return _loop


def set_main_loop(loop: MainLoop) -> None:
    global _loop
    _loop = loop
