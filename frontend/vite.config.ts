import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig(({ mode }) => ({
    base: mode === "production" ? "/app/" : "/",
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "src") },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": "http://localhost:8000",
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}", "test/**/*.test.{ts,tsx}"],
      exclude: ["e2e/**", "node_modules/**", "dist/**"],
      css: false,
    },
  }));
