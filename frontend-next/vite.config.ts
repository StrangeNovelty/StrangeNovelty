import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  base: "/static/story_engine_next/",
  build: {
    outDir: resolve(__dirname, "../static/story_engine_next"),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, "src/main.tsx"),
      output: { entryFileNames: "story-engine-next.js", assetFileNames: "story-engine-next.[ext]" },
    },
  },
});
