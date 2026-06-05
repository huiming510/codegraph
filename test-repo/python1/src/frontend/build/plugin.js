import vue from "@vitejs/plugin-vue";
import { createSvgIconsPlugin } from "vite-plugin-svg-icons";
import viteCompression from "vite-plugin-compression";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * 获取 Vite 插件列表
 * @param {Record<string, any>} viteEnv - conversionEnv 返回的配置
 * @returns {import('vite').PluginOption[]}
 */
export function getPlugins(viteEnv) {
  const { VITE_APP_BUILD_COMPRESS } = viteEnv;
  const plugins = [
    vue(),
    createSvgIconsPlugin({
      iconDirs: [resolve(__dirname, "../src/assets/svgs")],
      symbolId: "icon-[name]"
    })
  ];
  if (VITE_APP_BUILD_COMPRESS && VITE_APP_BUILD_COMPRESS !== "none") {
    plugins.push(
      viteCompression({
        algorithm: VITE_APP_BUILD_COMPRESS,
        deleteOriginFile: viteEnv.VITE_APP_BUILD_COMPRESS_DELETE_ORIGIN_FILE
      })
    );
  }
  return plugins;
}
