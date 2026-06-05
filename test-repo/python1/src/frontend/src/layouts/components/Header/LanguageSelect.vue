<template>
  <div class="header-lang">
    <a-dropdown v-model:open="open" :trigger="['click']">
      <span class="lang-trigger">
        <GlobalOutlined class="icon" />
        <span class="label">{{ currentLabel }}</span>
        <DownOutlined class="arrow" />
      </span>
      <template #overlay>
        <a-menu :selected-keys="[currentLocale]" @click="onSelect">
          <a-menu-item v-for="opt in options" :key="opt.value">
            {{ opt.label }}
          </a-menu-item>
        </a-menu>
      </template>
    </a-dropdown>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { GlobalOutlined, DownOutlined } from "@ant-design/icons-vue";
import { message } from "ant-design-vue";
import { useGlobalStore } from "@/stores/modules/global";
import { getLocaleApi, setLocaleApi } from "@/api/modules/locale";

const options = [
  { value: "zh", label: "中文" },
  { value: "ja", label: "日本語" },
  { value: "en", label: "English" }
];

const open = ref(false);
const globalStore = useGlobalStore();

const currentLocale = computed(() => {
  const lang = globalStore.language;
  return options.some(o => o.value === lang) ? lang : "zh";
});

const currentLabel = computed(() => {
  return options.find(o => o.value === currentLocale.value)?.label ?? "中文";
});

async function loadLocale() {
  try {
    const data = await getLocaleApi();
    if (data?.locale) globalStore.setLanguage(data.locale);
  } catch {
    globalStore.setLanguage("zh");
  }
}

async function onSelect({ key }) {
  if (key === currentLocale.value) {
    open.value = false;
    return;
  }
  try {
    await setLocaleApi(key);
    globalStore.setLanguage(key);
    message.success("语言已切换");
  } catch {
    message.error("切换失败");
  }
  open.value = false;
}

onMounted(() => {
  if (!globalStore.language) loadLocale();
});
</script>

<style scoped lang="scss">
.header-lang {
  display: flex;
  align-items: center;
  height: 32px;
  flex-shrink: 0;

  .lang-trigger {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    min-width: 100px;
    height: 32px;
    padding: 0 12px;
    color: rgb(0 0 0 / 65%);
    cursor: pointer;
    border: 1px solid #c7def5;
    border-radius: 16px;
    white-space: nowrap;
    transition: background-color 0.2s;

    &:hover {
      background-color: rgb(199 222 245 / 80%);
    }

    .icon {
      flex-shrink: 0;
      font-size: 14px;
    }

    .label {
      flex-shrink: 0;
      font-size: 14px;
      white-space: nowrap;
    }

    .arrow {
      flex-shrink: 0;
      margin-left: 2px;
      font-size: 10px;
      opacity: 0.7;
    }
  }
}

/* 下拉菜单项不挤压文字 */
:deep(.ant-dropdown-menu) {
  min-width: 100px;

  .ant-dropdown-menu-item {
    white-space: nowrap;
  }
}
</style>
