"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Brain } from "lucide-react";
import { api, getToken } from "@/lib/api";

type Vote = { strategy: string; direction: string; confidence: number; reasoning: string };
type SignalsResp = {
  symbol: string;
  timeframe: string;
  regime: string;
  ensemble: { direction: string; confidence: number; reasoning: string };
  votes: Vote[];
};

export default function StrategiesPage() {
  return (
    <Suspense fallback={<div className="p-6 text-muted">로딩...</div>}>
      <StrategiesInner />
    </Suspense>
  );
}

function StrategiesInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [symbol, setSymbol] = useState(params.get("symbol") ?? "KRW-BTC");
  const [data, setData] = useState<SignalsResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
  }, [router]);

  async function fetchSignals() {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const r = await api<SignalsResp>(`/strategies/signals/${symbol}?timeframe=1h`, { token });
      setData(r);
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
          <Brain className="w-5 h-5 text-info" />
          <span className="font-semibold">전략 신호 분석</span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="card p-5">
          <div className="flex flex-col md:flex-row md:items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm text-muted mb-1">종목 (Upbit)</label>
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="w-full px-3 py-2.5 rounded bg-bg border border-border focus:border-info outline-none"
                placeholder="KRW-BTC"
              />
            </div>
            <button
              onClick={fetchSignals}
              disabled={loading}
              className="btn btn-primary disabled:opacity-50"
            >
              {loading ? "분석 중..." : "신호 분석"}
            </button>
          </div>
          {error && <p className="text-down text-sm mt-3">{error}</p>}
        </div>

        {data && (
          <>
            <div className="card p-5">
              <h2 className="text-lg font-semibold mb-4">앙상블 결정</h2>
              <div className="flex items-center gap-4">
                <DirBadge dir={data.ensemble.direction} />
                <div>
                  <p className="text-sm text-muted">레짐: {data.regime}</p>
                  <p className="text-sm mt-1">
                    신뢰도: <b>{(data.ensemble.confidence * 100).toFixed(1)}%</b>
                  </p>
                </div>
              </div>
              <p className="text-muted text-sm mt-4">{data.ensemble.reasoning}</p>
            </div>

            <div className="card p-5">
              <h2 className="text-lg font-semibold mb-4">개별 전략 투표</h2>
              <div className="space-y-3">
                {data.votes.map((v) => (
                  <div
                    key={v.strategy}
                    className="p-4 rounded-lg bg-bg border border-border flex gap-4"
                  >
                    <DirBadge dir={v.direction} />
                    <div className="flex-1">
                      <p className="font-medium">{v.strategy}</p>
                      <p className="text-xs text-muted mt-1">
                        conf {(v.confidence * 100).toFixed(1)}%
                      </p>
                      <p className="text-sm text-muted mt-2 leading-relaxed">{v.reasoning}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function DirBadge({ dir }: { dir: string }) {
  const style =
    dir === "BUY"
      ? "bg-up/15 text-up border-up/30"
      : dir === "SELL"
      ? "bg-down/15 text-down border-down/30"
      : "bg-surface text-muted border-border";
  return (
    <span
      className={`px-4 py-2 rounded-lg text-sm font-medium border ${style}`}
      style={{ minWidth: 80, textAlign: "center" }}
    >
      {dir}
    </span>
  );
}
