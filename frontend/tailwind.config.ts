import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0b",
        surface: "#131316",
        border: "#27272a",
        muted: "#a1a1aa",
        fg: "#fafafa",
        up: "#22c55e",
        down: "#ef4444",
        warn: "#f59e0b",
        info: "#3b82f6",
      },
      fontFamily: {
        sans: ["Pretendard", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
