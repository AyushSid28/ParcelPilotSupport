import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/health": "http://127.0.0.1:8000", "/chat": "http://127.0.0.1:8000", "/ops": "http://127.0.0.1:8000", "/me": "http://127.0.0.1:8000", "/orders": "http://127.0.0.1:8000", "/tickets": "http://127.0.0.1:8000", "/personas": "http://127.0.0.1:8000", "/actions": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
