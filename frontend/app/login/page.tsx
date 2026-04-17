"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Bot } from "lucide-react";
import { login, saveToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const token = await login(username, password);
      saveToken(token);
      router.push("/dashboard");
    } catch (err) {
      setError("로그인 실패. 사용자명/비밀번호를 확인하세요.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <div className="card w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-6">
          <Bot className="w-7 h-7 text-info" />
          <h1 className="text-2xl font-semibold">QuantSage</h1>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-1">사용자명</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 rounded bg-bg border border-border focus:border-info outline-none"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm text-muted mb-1">비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 rounded bg-bg border border-border focus:border-info outline-none"
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-down text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full disabled:opacity-50"
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>
          <p className="text-xs text-muted">
            기본값: <code>admin</code> / <code>.env</code>의 <code>ADMIN_PASSWORD</code>
          </p>
        </form>
      </div>
    </main>
  );
}
