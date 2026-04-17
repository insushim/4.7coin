"""Walk-forward runner + HTML report.

Avoids a weasyprint/PDF dependency. The HTML report is self-contained (inline
CSS + base64 images) so it opens in any browser and prints to PDF cleanly.
"""

from __future__ import annotations

import base64
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import BacktestEngine, EngineConfig
from .metrics import PerformanceMetrics, compute_all, deflated_sharpe
from .simulator import BacktestResult, SimulatorConfig


@dataclass
class WindowResult:
    window_id: int
    start_bar: int
    end_bar: int
    metrics: PerformanceMetrics
    equity_curve: list[float] = field(default_factory=list)
    trades_pnl: list[float] = field(default_factory=list)


def run_walk_forward(
    df: pd.DataFrame,
    ensemble,
    *,
    train_bars: int = 1200,
    test_bars: int = 300,
    step_bars: int = 300,
    sim_config: SimulatorConfig | None = None,
    engine_config: EngineConfig | None = None,
) -> tuple[list[WindowResult], PerformanceMetrics]:
    """Slide the window; fit-free (strategies are parameter-free by design).

    Returns per-window metrics plus an aggregate over concatenated test returns.
    """
    n = len(df)
    results: list[WindowResult] = []
    all_returns: list[pd.Series] = []
    all_equity_start = float(engine_config.initial_equity if engine_config else 10_000_000)
    running_equity = all_equity_start
    start = 0
    window_id = 0
    while start + train_bars + test_bars <= n:
        test = df.iloc[start + train_bars : start + train_bars + test_bars].copy()
        engine = BacktestEngine(
            ensemble,
            sim_config=sim_config,
            engine_config=EngineConfig(
                initial_equity=running_equity,
                bet_fraction=(engine_config.bet_fraction if engine_config else 0.1),
                take_profit_pct=(engine_config.take_profit_pct if engine_config else 0.03),
                stop_loss_pct=(engine_config.stop_loss_pct if engine_config else 0.015),
                max_hold_bars=(engine_config.max_hold_bars if engine_config else 48),
                periods_per_year=(engine_config.periods_per_year if engine_config else 252 * 24),
            ),
        )
        result, metrics = engine.run(test)
        results.append(
            WindowResult(
                window_id=window_id,
                start_bar=start + train_bars,
                end_bar=start + train_bars + test_bars,
                metrics=metrics,
                equity_curve=list(result.equity_curve.values),
                trades_pnl=[t.pnl for t in result.trades],
            )
        )
        all_returns.append(result.equity_curve.pct_change().dropna())
        running_equity = result.final_equity
        start += step_bars
        window_id += 1

    concat = pd.concat(all_returns) if all_returns else pd.Series(dtype=float)
    agg_equity = (1 + concat).cumprod() * all_equity_start if not concat.empty else pd.Series([all_equity_start])
    trades_flat = [p for w in results for p in w.trades_pnl]
    aggregate = compute_all(
        concat,
        agg_equity,
        trades_flat,
        periods_per_year=(engine_config.periods_per_year if engine_config else 252 * 24),
        n_trials=max(1, len(results)),
    )
    return results, aggregate


def _chart_png_b64(y: list[float], title: str, color: str = "#22c55e") -> str:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 3), dpi=120, facecolor="#0a0a0b")
        ax.set_facecolor("#131316")
        ax.plot(y, color=color, linewidth=1.5)
        ax.set_title(title, color="#fafafa", fontsize=11)
        ax.tick_params(colors="#a1a1aa", labelsize=8)
        for sp in ax.spines.values():
            sp.set_color("#27272a")
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor="#0a0a0b")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def render_html(
    windows: list[WindowResult], aggregate: PerformanceMetrics, *, symbol: str, timeframe: str
) -> str:
    generated = datetime.now(tz=__import__("datetime").UTC).strftime("%Y-%m-%d %H:%M UTC")
    per_window_rows = "".join(
        f"""
        <tr>
          <td>{w.window_id}</td>
          <td>{w.start_bar}→{w.end_bar}</td>
          <td>{w.metrics.total_return:.2%}</td>
          <td>{w.metrics.sharpe:.2f}</td>
          <td>{w.metrics.max_drawdown:.2%}</td>
          <td>{w.metrics.win_rate:.1%}</td>
          <td>{w.metrics.n_trades}</td>
        </tr>
        """
        for w in windows
    )
    # assemble aggregate equity curve
    agg_curve: list[float] = []
    running = 1.0
    for w in windows:
        if not w.equity_curve:
            continue
        base = w.equity_curve[0]
        for v in w.equity_curve:
            agg_curve.append(running * (v / base))
        if w.equity_curve:
            running = agg_curve[-1]
    b64 = _chart_png_b64(agg_curve, f"{symbol} Walk-Forward Equity (normalized)")
    img_tag = f'<img src="data:image/png;base64,{b64}" alt="equity curve"/>' if b64 else "<p>Chart unavailable (matplotlib not installed)</p>"

    verdict_row = lambda label, val, good, bad: (  # noqa: E731
        f'<tr><td>{label}</td><td style="color:{"#22c55e" if good else ("#ef4444" if bad else "#fafafa")}">{val}</td></tr>'
    )
    checks = [
        verdict_row(
            "Windows profitable ≥70%",
            f"{sum(1 for w in windows if w.metrics.total_return > 0)}/{len(windows)}",
            good=(sum(1 for w in windows if w.metrics.total_return > 0) / max(1, len(windows)) >= 0.7),
            bad=(sum(1 for w in windows if w.metrics.total_return > 0) / max(1, len(windows)) < 0.5),
        ),
        verdict_row(
            "Aggregate Sharpe > 1.0",
            f"{aggregate.sharpe:.2f}",
            good=aggregate.sharpe > 1.0,
            bad=aggregate.sharpe < 0.5,
        ),
        verdict_row(
            "Max Drawdown > -25%",
            f"{aggregate.max_drawdown:.2%}",
            good=aggregate.max_drawdown > -0.15,
            bad=aggregate.max_drawdown < -0.25,
        ),
        verdict_row(
            "Deflated Sharpe > 0.5",
            f"{aggregate.deflated_sharpe:.3f}",
            good=aggregate.deflated_sharpe > 0.5,
            bad=aggregate.deflated_sharpe < 0.2,
        ),
    ]

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>QuantSage Walk-Forward — {symbol}</title>
<style>
  body {{ background:#0a0a0b; color:#fafafa; font-family:"Pretendard","Inter",system-ui,sans-serif; padding:2rem; line-height:1.5; }}
  h1 {{ color:#3b82f6; margin:0 0 0.5rem 0; }}
  h2 {{ border-bottom:1px solid #27272a; padding-bottom:0.5rem; margin-top:2rem; }}
  .card {{ background:#131316; border:1px solid #27272a; border-radius:12px; padding:1.5rem; margin:1rem 0; }}
  table {{ width:100%; border-collapse:collapse; margin-top:0.5rem; }}
  th, td {{ padding:0.5rem 0.75rem; border-bottom:1px solid #27272a; text-align:left; }}
  th {{ color:#a1a1aa; font-weight:500; font-size:0.85rem; text-transform:uppercase; }}
  .metric {{ display:inline-block; padding:0.5rem 1rem; margin:0.25rem; background:#1c1c1f; border-radius:8px; }}
  .metric b {{ display:block; font-size:1.5rem; color:#fafafa; }}
  .metric span {{ font-size:0.8rem; color:#a1a1aa; }}
  img {{ max-width:100%; border-radius:8px; }}
  .warn {{ background:#78350f; border-left:4px solid #f59e0b; padding:1rem; border-radius:4px; margin:1rem 0; }}
</style></head><body>
  <h1>QuantSage — Walk-Forward Report</h1>
  <p style="color:#a1a1aa">{symbol} · {timeframe} · generated {generated}</p>

  <div class="warn">
    ⚠️ 이 보고서의 모든 결과는 과거 데이터 시뮬레이션이며 미래 수익을 보장하지 않습니다.
    실거래 전 Paper Trading 최소 30일 + Kill-Switch 수동 검증 필수.
  </div>

  <h2>Aggregate Metrics (out-of-sample concatenated)</h2>
  <div class="card">
    <div class="metric"><b>{aggregate.total_return:.2%}</b><span>Total Return</span></div>
    <div class="metric"><b>{aggregate.sharpe:.2f}</b><span>Sharpe</span></div>
    <div class="metric"><b>{aggregate.sortino:.2f}</b><span>Sortino</span></div>
    <div class="metric"><b>{aggregate.calmar:.2f}</b><span>Calmar</span></div>
    <div class="metric"><b>{aggregate.max_drawdown:.2%}</b><span>Max DD</span></div>
    <div class="metric"><b>{aggregate.win_rate:.1%}</b><span>Win Rate</span></div>
    <div class="metric"><b>{aggregate.profit_factor:.2f}</b><span>Profit Factor</span></div>
    <div class="metric"><b>{aggregate.deflated_sharpe:.3f}</b><span>Deflated Sharpe</span></div>
    <div class="metric"><b>{aggregate.n_trades}</b><span>Trades</span></div>
  </div>

  <h2>Validation Checklist</h2>
  <div class="card"><table>
    <thead><tr><th>Criterion</th><th>Result</th></tr></thead>
    <tbody>{"".join(checks)}</tbody>
  </table></div>

  <h2>Equity Curve</h2>
  <div class="card">{img_tag}</div>

  <h2>Per-Window Breakdown</h2>
  <div class="card"><table>
    <thead><tr>
      <th>Window</th><th>Bars</th><th>Return</th><th>Sharpe</th>
      <th>MDD</th><th>Win %</th><th>Trades</th>
    </tr></thead>
    <tbody>{per_window_rows}</tbody>
  </table></div>
</body></html>
"""


def save_report(
    windows: list[WindowResult],
    aggregate: PerformanceMetrics,
    *,
    symbol: str,
    timeframe: str,
    out_dir: str | Path = "data/reports",
) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=__import__("datetime").UTC).strftime("%Y%m%d_%H%M%S")
    html_path = out / f"walk_forward_{symbol}_{timeframe}_{ts}.html"
    json_path = html_path.with_suffix(".json")
    html_path.write_text(render_html(windows, aggregate, symbol=symbol, timeframe=timeframe))
    json_path.write_text(
        json.dumps(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "generated_at": datetime.now(tz=__import__("datetime").UTC).isoformat(),
                "aggregate": asdict(aggregate),
                "windows": [
                    {
                        "window_id": w.window_id,
                        "start_bar": w.start_bar,
                        "end_bar": w.end_bar,
                        "metrics": asdict(w.metrics),
                    }
                    for w in windows
                ],
            },
            ensure_ascii=False,
            indent=2,
            default=float,
        )
    )
    return html_path
