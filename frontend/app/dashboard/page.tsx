"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bot,
  Wallet,
  Activity,
  AlertTriangle,
  Power,
  LogOut,
  BarChart3,
  Brain,
} from "lucide-react";
import { api, getToken, clearToken } from "@/lib/api";

type HealthResp = {
  status: string;
  trading_mode: string;
  live_enabled: boolean;
  kill_switch: { active: boolean; reason: string | null; message: string };
};
type StatusResp = {
  loop: {
    running: boolean;
    iterations: number;
    last_regime: string | null;
    last_error: string;
    symbols: string[];
  };
};
type PositionsResp = {
  cash_krw: string;
  positions: { symbol: string; amount: string; avg_entry: string }[];
  trade_log_tail: unknown[];
};

export default function DashboardPage() {
  const router = useRouter();
  const [health, setHealth] = useState<HealthResp | null>(null);
  const [status, setStatus] = useState<StatusResp | null>(null);
  const [positions, setPositions] = useState<PositionsResp | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    const load = async () => {
      try {
        const [h, s, p] = await Promise.all([
          api<HealthResp>("/health"),
          api<StatusResp>("/admin/status", { token }),
          api<PositionsResp>("/positions", { token }),
        ]);
        setHealth(h);
        setStatus(s);
        setPositions(p);
      } catch (e) {
        setError(String(e));
      }
    };
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [router]);

  async function kill() {
    if (!confirm("정말 Kill-Switch를 작동하시겠습니까? 모든 신규 주문이 중단됩니다.")) return;
    const token = getToken();
    if (!token) return;
    try {
      await api("/admin/kill", { method: "POST", token });
      alert("Kill-Switch 작동됨");
    } catch (e) {
      alert(`실패: ${e}`);
    }
  }

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-border sticky top-0 bg-bg/90 backdrop-blur z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="w-6 h-6 text-info" />
            <span className="font-semibold">QuantSage</span>
            <span className="text-xs px-2 py-0.5 rounded bg-surface text-muted">
              {health?.trading_mode?.toUpperCase() ?? "—"}
            </span>
            {health?.kill_switch.active && (
              <span className="text-xs px-2 py-0.5 rounded bg-down/20 text-down">KILLED</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Link href="/backtest" className="btn btn-ghost inline-flex items-center gap-2">
              <BarChart3 className="w-4 h-4" /> 백테스트
            </Link>
            <Link href="/strategies" className="btn btn-ghost inline-flex items-center gap-2">
              <Brain className="w-4 h-4" /> 전략
            </Link>
            <button onClick={kill} className="btn btn-danger inline-flex items-center gap-2">
              <Power className="w-4 h-4" /> Kill-Switch
            </button>
            <button onClick={logout} className="btn btn-ghost inline-flex items-center gap-2">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {error && (
          <div className="card p-4 flex gap-3 border-down/50">
            <AlertTriangle className="w-5 h-5 text-down" />
            <div>
              <p className="text-down font-medium">백엔드 연결 실패</p>
              <p className="text-muted text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-4">
          <Stat
            icon={<Wallet className="w-5 h-5 text-info" />}
            label="Paper 현금"
            value={positions ? `${Number(positions.cash_krw).toLocaleString("ko-KR")} KRW` : "—"}
          />
          <Stat
            icon={<Activity className="w-5 h-5 text-up" />}
            label="진행 상태"
            value={
              status
                ? `${status.loop.running ? "실행 중" : "대기"} · ${status.loop.iterations} 회`
                : "—"
            }
          />
          <Stat
            icon={<Brain className="w-5 h-5 text-warn" />}
            label="현재 레짐"
            value={status?.loop.last_regime ?? "측정 중"}
          />
        </div>

        <div className="card p-5">
          <h2 className="text-lg font-semibold mb-4">보유 포지션</h2>
          {positions?.positions.length ? (
            <table className="w-full">
              <thead>
                <tr className="text-muted text-xs uppercase tracking-wide text-left">
                  <th className="py-2">종목</th>
                  <th className="py-2">수량</th>
                  <th className="py-2">평균 진입가</th>
                </tr>
              </thead>
              <tbody>
                {positions.positions.map((p) => (
                  <tr key={p.symbol} className="border-t border-border">
                    <td className="py-3 font-medium">{p.symbol}</td>
                    <td className="py-3">{Number(p.amount).toFixed(8)}</td>
                    <td className="py-3">{Number(p.avg_entry).toLocaleString("ko-KR")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-muted text-sm">보유 포지션 없음 (Paper).</p>
          )}
        </div>

        <div className="card p-5">
          <h2 className="text-lg font-semibold mb-4">감시 종목</h2>
          <div className="flex flex-wrap gap-2">
            {status?.loop.symbols.map((s) => (
              <Link
                key={s}
                href={`/strategies?symbol=${s}`}
                className="px-4 py-2 rounded-full bg-surface border border-border text-sm hover:border-info"
              >
                {s}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 text-muted text-sm">
        {icon}
        {label}
      </div>
      <p className="text-2xl font-semibold mt-2">{value}</p>
    </div>
  );
}
