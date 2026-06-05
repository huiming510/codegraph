import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  server: {
    host: true,
    port: 5173,
  },
  preview: {
    host: true,
    port: 4173,
  },
  build: {
    rollupOptions: {
      input: {
        kb: resolve(__dirname, "index.html"),
        chat: resolve(__dirname, "chat.html"),
      },
    },
  },
});
