/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#070d1c",
          900: "#0a1226",
          800: "#0f1a33",
          700: "#152340",
          600: "#1c2e52",
        },
        ink: "#e6edf7",
        muted: "#8aa0c2",
        accent: {
          DEFAULT: "#3b82f6",
          bright: "#2563eb",
          cyan: "#38bdf8",
        },
        risk: {
          low: "#16a34a",
          med: "#f59e0b",
          high: "#dc2626",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Arial", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(59,130,246,0.15), 0 8px 30px rgba(2,8,23,0.45)",
        card: "0 4px 24px rgba(2,8,23,0.35)",
      },
      backgroundImage: {
        "grid-faint":
          "radial-gradient(circle at 1px 1px, rgba(148,163,184,0.08) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
};
