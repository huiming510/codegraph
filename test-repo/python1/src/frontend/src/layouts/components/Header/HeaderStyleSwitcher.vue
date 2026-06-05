<template>
  <a-dropdown :trigger="['click']" placement="bottomRight">
    <span class="header-style-trigger">
      <BgColorsOutlined class="trigger-icon" />
      <span class="trigger-label">{{ t("headerStyle.label") }}</span>
    </span>
    <template #overlay>
      <a-menu :selected-keys="[globalStore.headerStyle]" @click="handleSelect">
        <a-menu-item key="light">{{ t("headerStyle.light") }}</a-menu-item>
        <a-menu-item key="dark">{{ t("headerStyle.dark") }}</a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</template>

<script setup>
import { BgColorsOutlined } from "@ant-design/icons-vue";
import { useGlobalStore } from "@/stores/modules/global";
import { useLocale } from "@/composables/useLocale";

const { t } = useLocale();
const globalStore = useGlobalStore();

function handleSelect({ key }) {
  globalStore.setHeaderStyle(key);
}
</script>

<style scoped lang="scss">
.header-style-trigger {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  white-space: nowrap;
  cursor: pointer;
  border: 1px solid rgb(255 255 255 / 20%);
  border-radius: 16px;
  transition: background-color 0.2s;

  .trigger-icon {
    font-size: 14px;
    color: #8b949e;
  }

  .trigger-label {
    font-size: 14px;
    color: #8b949e;
  }

  &:hover {
    background-color: rgb(255 255 255 / 8%);

    .trigger-icon,
    .trigger-label {
      color: #e6edf3;
    }
  }
}
</style>
