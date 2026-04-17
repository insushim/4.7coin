const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type HttpMethod = "GET" | "POST" | "DELETE";

export async function api<T>(
  path: string,
  opts: { method?: HttpMethod; body?: unknown; token?: string } = {}
): Promise<T> {
  const { method = "GET", body, token } = opts;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export async function login(username: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${API_BASE}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("login failed");
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export function saveToken(token: string): void {
  if (typeof window !== "undefined") localStorage.setItem("qs_token", token);
}
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("qs_token");
}
export function clearToken(): void {
  if (typeof window !== "undefined") localStorage.removeItem("qs_token");
}
