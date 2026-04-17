"""Performance metrics including Deflated Sharpe Ratio.

DSR is critical for honesty: it adjusts Sharpe for the number of trials and
non-normality so overfit "great" backtests don't pass without scrutiny.
Source: Lopez de Prado, "Advances in Financial Machine Learning".
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PerformanceMetrics:
    total_return: float
    annual_return: float
    annual_vol: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    win_rate: float
    profit_factor: float
    deflated_sharpe: float
    n_trades: int


def _annualize(returns: pd.Series, periods_per_year: int) -> tuple[float, float]:
    mean = returns.mean() * periods_per_year
    std = returns.std() * math.sqrt(periods_per_year)
    return float(mean), float(std)


def sharpe_ratio(returns: pd.Series, periods_per_year: int, rf: float = 0.0) -> float:
    mean, std = _annualize(returns, periods_per_year)
    return (mean - rf) / std if std > 0 else 0.0


def sortino_ratio(returns: pd.Series, periods_per_year: int, rf: float = 0.0) -> float:
    mean, _ = _annualize(returns, periods_per_year)
    downside = returns[returns < 0]
    if len(downside) == 0:
        return float("inf") if mean > 0 else 0.0
    downside_std = downside.std() * math.sqrt(periods_per_year)
    return (mean - rf) / downside_std if downside_std > 0 else 0.0


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min())


def deflated_sharpe(returns: pd.Series, periods_per_year: int, n_trials: int = 1) -> float:
    """Deflated Sharpe Ratio (Lopez de Prado 2014).

    Penalises Sharpe when many trials are run — signals likely luck, not skill.
    """
    n = len(returns)
    if n < 30:
        return 0.0
    sr = sharpe_ratio(returns, periods_per_year)
    skew = float(returns.skew())
    kurt = float(returns.kurtosis())

    # Expected maximum SR after n_trials (Gaussian multiple-testing)
    if n_trials < 2:
        expected_max_sr = 0.0
    else:
        euler_mascheroni = 0.5772
        expected_max_sr = math.sqrt(2 * math.log(n_trials)) - (
            (euler_mascheroni + math.log(math.log(n_trials))) / math.sqrt(2 * math.log(n_trials))
        )
    numerator = (sr - expected_max_sr) * math.sqrt(n - 1)
    denominator = math.sqrt(max(1e-9, 1 - skew * sr + ((kurt - 1) / 4) * sr**2))
    from scipy.stats import norm

    return float(norm.cdf(numerator / denominator))


def compute_all(
    returns: pd.Series,
    equity: pd.Series,
    trades_pnl: list[float],
    periods_per_year: int = 252 * 24,  # default hourly
    n_trials: int = 1,
) -> PerformanceMetrics:
    annual_mean, annual_vol = _annualize(returns, periods_per_year)
    sr = sharpe_ratio(returns, periods_per_year)
    sor = sortino_ratio(returns, periods_per_year)
    mdd = max_drawdown(equity)
    total = float((equity.iloc[-1] / equity.iloc[0]) - 1) if len(equity) > 1 else 0.0
    calmar = annual_mean / abs(mdd) if mdd < 0 else 0.0
    wins = [p for p in trades_pnl if p > 0]
    losses = [p for p in trades_pnl if p < 0]
    win_rate = len(wins) / len(trades_pnl) if trades_pnl else 0.0
    pf = (
        (sum(wins) / abs(sum(losses)))
        if losses and sum(losses) != 0
        else float("inf") if wins else 0.0
    )
    dsr = deflated_sharpe(returns, periods_per_year, n_trials)
    return PerformanceMetrics(
        total_return=total,
        annual_return=annual_mean,
        annual_vol=annual_vol,
        sharpe=sr,
        sortino=sor,
        max_drawdown=mdd,
        calmar=calmar,
        win_rate=win_rate,
        profit_factor=float(pf) if np.isfinite(pf) else 0.0,
        deflated_sharpe=dsr,
        n_trades=len(trades_pnl),
    )
