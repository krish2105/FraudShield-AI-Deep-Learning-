/** @type {import('tailwindcss').Config} */

// Colors are backed by CSS variables (space-separated RGB channels) so the whole
// app supports light + dark themes from a single set of utility classes. The
// `navy-*` names keep their luminance ROLE (950 = page bg … 600 = border); the
// actual values flip between themes via the variables defined in index.css.
const v = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: v("--c-bg"),        // app / page background
          900: v("--c-surface-2"), // inputs, table headers
          800: v("--c-surface"),   // card surface
          700: v("--c-elev"),      // hover / pills / elevated
          600: v("--c-border"),    // borders
        },
        ink: v("--c-text"),
        muted: v("--c-muted"),
        accent: {
          DEFAULT: "#3b82f6",
          bright: "#2563eb",
          cyan: "#0ea5e9",
        },
        risk: {
          low: "#16a34a",
          med: "#f59e0b",
          high: "#dc2626",
        },
        // status text colors that flip per theme (for banners / alerts)
        tone: {
          warn: v("--c-warn"),
          info: v("--c-info"),
          danger: v("--c-danger"),
          ok: v("--c-ok"),
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Arial", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(59,130,246,0.18), 0 8px 30px rgba(2,8,23,0.25)",
        card: "var(--shadow-card)",
      },
      backgroundImage: {
        "grid-faint":
          "radial-gradient(circle at 1px 1px, rgb(var(--c-muted) / 0.10) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
};
