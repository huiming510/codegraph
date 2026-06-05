import { defineStore } from "pinia";
import piniaPersistConfig from "@/stores/helper/persist";

// 全局状态：语言、亮/暗主题（默认亮色）
export const useGlobalStore = defineStore("GlobalState", {
  state: () => ({
    language: "",
    /** 主题：'light' 亮色 | 'dark' 暗色，默认亮色 */
    theme: "light"
  }),
  getters: {},
  actions: {
    setLanguage(language) {
      this.language = language;
    },
    /** 切换/设置主题，并同步到 html 类名供全局样式使用 */
    setTheme(theme) {
      this.theme = theme === "dark" ? "dark" : "light";
      if (typeof document !== "undefined") {
        document.documentElement.classList.toggle("theme-dark", this.theme === "dark");
      }
    }
  },
  persist: piniaPersistConfig("global")
});
