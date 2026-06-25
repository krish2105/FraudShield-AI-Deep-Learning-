import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the built app works when opened from any path / static host.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    open: true,
    // Proxy API calls to the FastAPI backend during development.
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
