import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config — dev proxy gọi FastAPI ở :8000, tránh CORS khi dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
