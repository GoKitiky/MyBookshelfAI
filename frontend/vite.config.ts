import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local dev: localhost. Docker Compose sets http://api:8000 (see docker-compose.yml).
const apiProxyTarget =
  process.env.API_PROXY_TARGET?.trim() || "http://localhost:8000";

// Keep all backend routes under /api so SPA paths like /recommendations and
// /profile are not proxied on full page reload (GET would hit API and 405 or
// return JSON instead of index.html).
const proxy = {
  "/api": { target: apiProxyTarget, changeOrigin: true },
  "/health": { target: apiProxyTarget, changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    host: true,
    proxy,
  },
});
