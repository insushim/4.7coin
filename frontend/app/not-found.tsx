import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-5xl font-bold">404</h1>
        <p className="text-muted mt-2">페이지를 찾을 수 없습니다</p>
        <Link href="/" className="btn btn-primary mt-6 inline-block">
          홈으로
        </Link>
      </div>
    </main>
  );
}
