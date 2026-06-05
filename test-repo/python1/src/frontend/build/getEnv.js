/**
 * 将 Vite 加载的 env 转为配置对象，并设置默认值
 * @param {Record<string, string>} env - loadEnv 返回的环境变量
 * @returns {Record<string, any>}
 */
export function conversionEnv(env) {
  const publicPath =
    env.VITE_APP_PUBLIC_PATH && env.VITE_APP_PUBLIC_PATH !== "true" && env.VITE_APP_PUBLIC_PATH !== "false"
      ? env.VITE_APP_PUBLIC_PATH
      : "./";

  return {
    ...env,
    ...env,
    VITE_APP_PUBLIC_PATH: publicPath,
    VITE_APP_PORT: Number(env.VITE_APP_PORT) || 5174,
    VITE_OPEN: env.VITE_OPEN === "true",
    VITE_APP_PROXY: env.VITE_APP_PROXY !== "false",
    VITE_APP_DROP_CONSOLE_DEBUG: env.VITE_APP_DROP_CONSOLE_DEBUG === "true",
    VITE_APP_BUILD_COMPRESS: env.VITE_APP_BUILD_COMPRESS || "none",
    VITE_APP_BUILD_COMPRESS_DELETE_ORIGIN_FILE: env.VITE_APP_BUILD_COMPRESS_DELETE_ORIGIN_FILE === "true"
  };
}
