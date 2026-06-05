/**
 * 多语言 composable：根据 globalStore.language 返回 t(key)
 * 使用 locale 作为依赖（如 :key="locale"）以保证语言切换后界面更新
 */
import { computed } from "vue";
import { useGlobalStore } from "@/stores/modules/global";
import { t as tRaw } from "@/locales";

export function useLocale() {
  const globalStore = useGlobalStore();
  const locale = computed(() => globalStore.language || "zh");
  const t = key => tRaw(locale.value, key);
  return { t, locale };
}
