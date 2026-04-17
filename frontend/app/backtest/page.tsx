"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3 } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api, getToken } from "@/lib/api";

type BacktestResp = {
  symbol: string;
  total_return: number;
  initial_equity: number;
  final_equity: number;
  metrics: {
    sharpe: number;
    sortino: number;
    max_drawdown: number;
    calmar: number;
    win_rate: number;
    profit_factor: number;
    deflated_sharpe: number;
    n_trades: number;
  };
  equity_curve_tail: { i: number; equity: number }[];
  trades: {
    entry_ts: number;
    exit_ts: number | null;
    direction: string;
    entry_price: number;
    exit_price: number | null;
    pnl: number;
    reason_entry: string;
    reason_exit: string;
  }[];
};

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("KRW-BTC");
  const [bars, setBars] = useState(200);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BacktestResp | null>(null);

  async function run() {
    const token = getToken();
    if (!token) {
      setError("로그인이 필요합니다");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const r = await api<BacktestResp>(
        `/backtest/run?symbol=${symbol}&timeframe=1h&bars=${bars}`,
        { method: "POST", token }
      );
      setResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
          <Link href="/dashboard" className="btn btn-ghost inline-flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <BarChart3 className="w-5 h-5 text-info" />
          <span className="font-semibold">백테스트</span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="card p-5">
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-muted mb-1">종목</label>
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="w-full px-3 py-2.5 rounded bg-bg border border-border outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-muted mb-1">바 수 (최대 200)</label>
              <input
                type="number"
                value={bars}
                onChange={(e) => setBars(Number(e.target.value))}
                className="w-full px-3 py-2.5 rounded bg-bg border border-border outline-none"
              />
            </div>
            <div className="flex items-end">
              <button onClick={run} disabled={loading} className="btn btn-primary w-full disabled:opacity-50">
                {loading ? "실행 중..." : "백테스트 실행"}
              </button>
            </div>
          </div>
          {error && <p className="text-down text-sm mt-3">{error}</p>}
        </div>

        {result && (
          <>
            <div className="grid md:grid-cols-4 gap-4">
              <Metric label="총 수익률" value={`${(result.total_return * 100).toFixed(2)}%`} good={result.total_return > 0} />
              <Metric label="Sharpe" value={result.metrics.sharpe.toFixed(2)} good={result.metrics.sharpe > 1} />
              <Metric
                label="MDD"
                value={`${(result.metrics.max_drawdown * 100).toFixed(2)}%`}
                good={result.metrics.max_drawdown > -0.15}
              />
              <Metric label="거래 수" value={String(result.metrics.n_trades)} />
            </div>

            <div className="card p-5">
              <h2 className="text-lg font-semibold mb-4">Equity Curve (tail)</h2>
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer>
                  <LineChart data={result.equity_curve_tail}>
                    <XAxis dataKey="i" stroke="#a1a1aa" />
                    <YAxis stroke="#a1a1aa" />
                    <Tooltip contentStyle={{ background: "#131316", border: "1px solid #27272a" }} />
                    <Line type="monotone" dataKey="equity" stroke="#22c55e" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card p-5">
              <h2 className="text-lg font-semibold mb-4">상세 지표</h2>
              <div className="grid md:grid-cols-3 gap-4 text-sm">
                <Row k="Sortino" v={result.metrics.sortino.toFixed(2)} />
                <Row k="Calmar" v={result.metrics.calmar.toFixed(2)} />
                <Row k="Deflated Sharpe" v={result.metrics.deflated_sharpe.toFixed(3)} />
                <Row k="Win Rate" v={`${(result.metrics.win_rate * 100).toFixed(1)}%`} />
                <Row k="Profit Factor" v={result.metrics.profit_factor.toFixed(2)} />
                <Row k="초기 자본" v={result.initial_equity.toLocaleString("ko-KR")} />
                <Row k="최종 자본" v={result.final_equity.toLocaleString("ko-KR")} />
              </div>
            </div>

            <div className="card p-5">
              <h2 className="text-lg font-semibold mb-4">최근 거래</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted text-xs uppercase tracking-wide text-left">
                    <th className="py-2">진입</th>
                    <th className="py-2">방향</th>
                    <th className="py-2">진입가</th>
                    <th className="py-2">청산가</th>
                    <th className="py-2">P&L</th>
                    <th className="py-2">청산 사유</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="py-2">{t.entry_ts}</td>
                      <td className="py-2">{t.direction}</td>
                      <td className="py-2">{t.entry_price.toFixed(2)}</td>
                      <td className="py-2">{t.exit_price?.toFixed(2) ?? "—"}</td>
                      <td className={`py-2 ${t.pnl >= 0 ? "text-up" : "text-down"}`}>
                        {t.pnl.toFixed(2)}
                      </td>
                      <td className="py-2 text-muted">{t.reason_exit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function Metric({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="card p-5">
      <p className="text-muted text-sm">{label}</p>
      <p
        className={`text-2xl font-semibold mt-2 ${
          good === undefined ? "" : good ? "text-up" : "text-down"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between py-2 border-b border-border">
      <span className="text-muted">{k}</span>
      <span className="font-medium">{v}</span>
    </div>
  );
}
