import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    // recharts alone minifies to ~565 kB (~160 kB gzip); it is split out below.
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        // Keep the charting library in its own cacheable chunk.
        manualChunks: { charts: ["recharts"] },
      },
    },
  },
});
