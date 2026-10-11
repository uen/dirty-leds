import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev the Python app serves the API on :6923 (python3 main.py)
export default defineConfig({
  plugins: [react()],
  // three.js alone is ~600 kB; this is served locally, so one bundle is fine
  build: { chunkSizeWarningLimit: 1000 },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:6923",
    },
  },
});
