import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QuantSage — AI Crypto Trader",
  description: "Risk-first, explainable, regime-aware crypto trading dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="dark">
      <body>{children}</body>
    </html>
  );
}
