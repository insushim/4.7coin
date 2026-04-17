"use client";

import Link from "next/link";
import { AlertTriangle } from "lucide-react";

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <div className="card p-8 max-w-md w-full">
        <AlertTriangle className="w-8 h-8 text-down mb-4" />
        <h1 className="text-2xl font-semibold">문제가 발생했습니다</h1>
        <p className="text-muted text-sm mt-2">{error.message}</p>
        <div className="flex gap-3 mt-6">
          <button onClick={reset} className="btn btn-primary">다시 시도</button>
          <Link href="/" className="btn btn-ghost">홈으로</Link>
        </div>
      </div>
    </main>
  );
}
