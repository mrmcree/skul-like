import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// The FastAPI backend (python tools/asset_studio.py) runs on 8765.
// `npm run dev` proxies the API and files to it; `npm run build` writes dist/,
// which the backend then serves at http://127.0.0.1:8765 by itself.
const BACKEND = "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": BACKEND, "/files": BACKEND },
  },
  build: { outDir: "dist", assetsDir: "studio-assets", emptyOutDir: true },
});
