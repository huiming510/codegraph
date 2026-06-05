<template>
  <div class="header-theme-toggle" :class="{ 'is-dark': isDark }">
    <span class="theme-trigger" :title="isDark ? '切换为亮色主题' : '切换为暗色主题'" @click="toggle">
      <BulbFilled v-if="isDark" class="icon icon-light" />
      <BulbOutlined v-else class="icon icon-dark" />
    </span>
  </div>
</template>

<script setup>
/**
 * Header 主题切换：亮色/暗色两种主题，默认亮色；点击图标切换，图标随当前主题切换（亮色时显示灯泡轮廓、暗色时显示实心灯泡）。
 */
import { computed, onMounted } from "vue";
import { BulbFilled, BulbOutlined } from "@ant-design/icons-vue";
import { useGlobalStore } from "@/stores/modules/global";

const globalStore = useGlobalStore();

const isDark = computed(() => globalStore.theme === "dark");

function toggle() {
  const next = isDark.value ? "light" : "dark";
  globalStore.setTheme(next);
}

onMounted(() => {
  // 持久化恢复后同步 html 类名（弹窗等全局样式依赖 html.theme-dark）
  document.documentElement.classList.toggle("theme-dark", globalStore.theme === "dark");
});
</script>

<style scoped lang="scss">
.header-theme-toggle {
  display: flex;
  align-items: center;
  height: 32px;
  flex-shrink: 0;
}

.theme-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: rgb(0 0 0 / 65%);
  cursor: pointer;
  border: 1px solid #c7def5;
  border-radius: 16px;
  transition:
    background-color 0.2s,
    color 0.2s;

  &:hover {
    background-color: rgb(199 222 245 / 80%);
  }

  .icon {
    font-size: 16px;
    flex-shrink: 0;
  }

  .icon-light {
    color: #faad14;
  }

  .icon-dark {
    color: rgb(0 0 0 / 55%);
  }
}

/* 暗色主题下触发器样式 */
.header-theme-toggle.is-dark .theme-trigger {
  color: rgb(255 255 255 / 75%);
  border-color: rgb(255 255 255 / 25%);

  &:hover {
    background-color: rgb(255 255 255 / 12%);
  }

  .icon-dark {
    color: rgb(255 255 255 / 65%);
  }

  .icon-light {
    color: #faad14;
  }
}
</style>
