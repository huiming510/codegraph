import { defineConfig, loadEnv } from "vite";
import { resolve } from "path";
import { conversionEnv } from "./build/getEnv";
import { getPlugins } from "./build/plugin";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const viteEnv = conversionEnv(env);

  return {
    base: viteEnv.VITE_APP_PUBLIC_PATH,
    plugins: getPlugins(viteEnv),
    resolve: {
      alias: {
        "@": resolve(__dirname, "./src")
      }
    },
    server: {
      host: "0.0.0.0",
      port: viteEnv.VITE_APP_PORT,
      open: viteEnv.VITE_OPEN,
      cors: true,
      proxy: {
        "/api": {
          target: viteEnv.VITE_APP_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true
        }
      }
    },
    esbuild: {
      drop: viteEnv.VITE_APP_DROP_CONSOLE_DEBUG ? ["console", "debugger"] : []
    },
    build: {
      outDir: "dist",
      minify: "esbuild",
      sourcemap: false,
      reportCompressedSize: false,
      chunkSizeWarningLimit: 2000,
      rollupOptions: {
        output: {
          chunkFileNames: "assets/js/[name]-[hash].js",
          entryFileNames: "assets/js/[name]-[hash].js",
          assetFileNames: "assets/[ext]/[name]-[hash].[ext]"
        }
      }
    }
  };
});
