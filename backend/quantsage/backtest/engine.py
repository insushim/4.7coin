"""Backtest engine — runs an ensemble strategy over historical OHLCV.

Bar-by-bar simulation: at each bar, regime is re-detected from the prefix
(no look-ahead), strategies produce signals, the ensemble votes, and the
simulator models fees + slippage on fills.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..features.regime import detect_regime
from ..strategies.base import Direction
from ..strategies.ensemble_voter import EnsembleVoter
from .metrics import PerformanceMetrics, compute_all
from .simulator import BacktestResult, Simulator, SimulatorConfig, Trade


@dataclass
class EngineConfig:
    initial_equity: float = 10_000_000  # 1천만 KRW
    bet_fraction: float = 0.1            # per-trade notional as equity fraction
    take_profit_pct: float = 0.03        # exit at +3%
    stop_loss_pct: float = 0.015         # exit at -1.5%
    max_hold_bars: int = 48              # time-based exit
    periods_per_year: int = 252 * 24     # hourly bars default


class BacktestEngine:
    def __init__(
        self,
        ensemble: EnsembleVoter,
        sim_config: SimulatorConfig | None = None,
        engine_config: EngineConfig | None = None,
    ):
        self.ensemble = ensemble
        self.sim = Simulator(sim_config)
        self.cfg = engine_config or EngineConfig()

    def run(self, df: pd.DataFrame, symbol: str = "BTC") -> tuple[BacktestResult, PerformanceMetrics]:
        if "close" not in df.columns:
            raise ValueError("df must contain OHLCV columns")
        df = df.copy().reset_index(drop=True)
        equity = self.cfg.initial_equity
        equity_curve: list[float] = []
        trades: list[Trade] = []
        open_trade: Trade | None = None
        min_history = 210

        for i in range(len(df)):
            row = df.iloc[i]
            close = float(row["close"])

            if open_trade:
                bars_held = i - int(open_trade.entry_ts)
                pnl_pct = (close - open_trade.entry_price) / open_trade.entry_price
                if open_trade.direction == Direction.SELL:
                    pnl_pct = -pnl_pct
                exit_now = False
                reason = ""
                if pnl_pct >= self.cfg.take_profit_pct:
                    exit_now, reason = True, "take-profit"
                elif pnl_pct <= -self.cfg.stop_loss_pct:
                    exit_now, reason = True, "stop-loss"
                elif bars_held >= self.cfg.max_hold_bars:
                    exit_now, reason = True, "time-exit"

                if exit_now:
                    exit_price = self.sim.fill_price(
                        close,
                        Direction.SELL if open_trade.direction == Direction.BUY else Direction.BUY,
                        float(row["high"]),
                        float(row["low"]),
                    )
                    notional_in = open_trade.amount * open_trade.entry_price
                    notional_out = open_trade.amount * exit_price
                    fees = self.sim.apply_fee(notional_in) + self.sim.apply_fee(notional_out)
                    pnl = (notional_out - notional_in) * (
                        1 if open_trade.direction == Direction.BUY else -1
                    ) - fees
                    open_trade.exit_ts = i
                    open_trade.exit_price = exit_price
                    open_trade.pnl = pnl
                    open_trade.reason_exit = reason
                    equity += pnl
                    trades.append(open_trade)
                    open_trade = None

            # New signal only when flat + enough history
            if open_trade is None and i >= min_history:
                sub = df.iloc[: i + 1]
                regime = detect_regime(sub)
                decision = self.ensemble.decide(sub, regime)
                if decision.direction in (Direction.BUY, Direction.SELL):
                    entry_price = self.sim.fill_price(
                        close, decision.direction, float(row["high"]), float(row["low"])
                    )
                    notional = equity * self.cfg.bet_fraction
                    amount = notional / entry_price
                    open_trade = Trade(
                        entry_ts=i,
                        exit_ts=None,
                        symbol=symbol,
                        direction=decision.direction,
                        entry_price=entry_price,
                        exit_price=None,
                        amount=amount,
                        pnl=0.0,
                        strategy="ensemble",
                        reason_entry=decision.reasoning,
                    )

            equity_curve.append(equity)

        equity_series = pd.Series(equity_curve, index=df.index)
        returns = equity_series.pct_change().dropna()
        trades_pnl = [t.pnl for t in trades]
        metrics = compute_all(
            returns,
            equity_series,
            trades_pnl,
            periods_per_year=self.cfg.periods_per_year,
            n_trials=1,
        )
        result = BacktestResult(
            trades=trades,
            equity_curve=equity_series,
            final_equity=equity,
            initial_equity=self.cfg.initial_equity,
            config=self.sim.config,
        )
        return result, metrics


def walk_forward(
    df: pd.DataFrame,
    ensemble: EnsembleVoter,
    train_bars: int = 2000,
    test_bars: int = 500,
    step_bars: int = 500,
    engine_config: EngineConfig | None = None,
) -> list[PerformanceMetrics]:
    """Walk-forward out-of-sample evaluation.

    Currently re-runs the engine on each test window. Strategy is parameter-free
    by design — hyperparameters live in ensemble weights which the ML models
    (future step) will retrain per window.
    """
    results: list[PerformanceMetrics] = []
    n = len(df)
    start = 0
    while start + train_bars + test_bars <= n:
        test = df.iloc[start + train_bars : start + train_bars + test_bars]
        engine = BacktestEngine(ensemble, engine_config=engine_config)
        _, metrics = engine.run(test)
        results.append(metrics)
        start += step_bars
    return results
