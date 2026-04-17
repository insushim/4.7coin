"use client";

import Link from "next/link";
import { Shield, BarChart3, Bot, AlertTriangle, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <header className="border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="w-7 h-7 text-info" />
            <span className="text-xl font-semibold">QuantSage</span>
            <span className="text-xs px-2 py-1 rounded bg-warn/20 text-warn">ALPHA · Paper Only</span>
          </div>
          <Link href="/login" className="btn btn-primary">
            대시보드 열기
          </Link>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-20">
        <h1 className="text-5xl font-bold leading-tight">
          AI 크립토 트레이더 <span className="text-info">QuantSage</span>
        </h1>
        <p className="text-muted text-xl mt-4 max-w-2xl">
          리스크 우선·설명 가능·레짐 인식·앙상블 투표. 수익을 보장하지 않지만, 손실을 최소화합니다.
        </p>
        <div className="mt-10 flex gap-3">
          <Link href="/login" className="btn btn-primary inline-flex items-center gap-2">
            시작하기 <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="https://github.com/insushim/4.7coin"
            target="_blank"
            className="btn btn-ghost"
            rel="noreferrer"
          >
            GitHub
          </a>
        </div>

        <div className="mt-16 grid md:grid-cols-3 gap-4">
          <Feature
            icon={<Shield className="w-5 h-5 text-info" />}
            title="8-Layer 리스크"
            body="Kelly/4, 변동성 타깃, 플래시 크래시 탐지, 다중 Kill-Switch."
          />
          <Feature
            icon={<Bot className="w-5 h-5 text-info" />}
            title="앙상블 전략"
            body="TrendFollowing · MeanReversion · Breakout · Grid · SmartDCA 5개 전략 투표."
          />
          <Feature
            icon={<BarChart3 className="w-5 h-5 text-info" />}
            title="정직한 백테스트"
            body="Walk-Forward · 슬리피지 · 수수료 · Deflated Sharpe로 오버피팅 방지."
          />
        </div>

        <div className="card p-5 mt-12 flex gap-4">
          <AlertTriangle className="w-6 h-6 text-warn flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-warn">중요 고지</p>
            <p className="text-muted mt-1 text-sm leading-relaxed">
              수익을 보장하지 않습니다. 첫 30일은 반드시 Paper Trading. 초기 실거래 자본은 총 자산의
              1–5%. API 키는 조회·주문 권한만 부여하고 출금 권한은 절대 금지. 본 소프트웨어는 본인 자산
              전용이며 타인 자금 운용은 불가합니다.
            </p>
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-6 text-center text-muted text-sm">
        QuantSage v0.1.0 · MIT · {new Date().getFullYear()}
      </footer>
    </main>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="font-semibold">{title}</h3>
      </div>
      <p className="text-muted text-sm mt-2 leading-relaxed">{body}</p>
    </div>
  );
}
