import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local dev: Vite serves the React app on 5173 and proxies /api and /ws
// to the FastAPI backend, so the browser never needs to know the backend's
// real address. In production the backend serves the built static files
// directly (see app/main.py), so no proxy is needed.
//
// The proxy target defaults to localhost:8000 for plain `npm run dev`, but
// is overridden to http://backend:8000 inside docker-compose (see
// docker-compose.yml's frontend service), since "localhost" inside that
// container refers to the frontend container itself, not the backend one.
const apiTarget = process.env.VITE_API_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/ws": {
        target: apiTarget.replace("http", "ws"),
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
