<template>
  <div class="sidebar-menu-full">
    <a-menu
      :selected-keys="selectedKeys"
      :open-keys="openKeys"
      :inline-collapsed="isCollapse"
      mode="inline"
      :items="menuItems"
      @click="handleClick"
      @open-change="handleOpenChange"
    />
    <div class="sidebar-collapse" @click="toggleCollapse">
      <MenuUnfoldOutlined v-if="isCollapse" class="collapse-icon" />
      <MenuFoldOutlined v-else class="collapse-icon" />
    </div>
  </div>
</template>

<script setup>
/**
 * 侧边栏全量菜单：一级 + 二级统一在侧边展示，供简洁风布局使用
 */
import { computed, ref, watch, h } from "vue";
import { useRoute, useRouter } from "vue-router";
import { MenuUnfoldOutlined, MenuFoldOutlined } from "@ant-design/icons-vue";
import { useAuthStore } from "@/stores/modules/auth";
import { MENU_HIDDEN_PATHS, getMenuTitle, MENU_CHILDREN_FALLBACK } from "@/constants/router";

const props = defineProps({
  collapsed: { type: Boolean, default: false }
});
const emit = defineEmits(["update:collapsed"]);

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const menuList = computed(() => {
  const raw = (authStore.authMenuListGet || []).filter(item => !item.meta?.isHide && !MENU_HIDDEN_PATHS.includes(item.path));
  return raw.map(item => {
    const children = item.children?.length ? item.children : MENU_CHILDREN_FALLBACK[item.path] || [];
    return { ...item, children };
  });
});

/** 转为 Ant Design Vue Menu 的 items 格式，保证子菜单能正确渲染进 ul */
function renderIcon(iconClass) {
  if (!iconClass) return undefined;
  return () => h("i", { class: ["iconfont", iconClass] });
}

const menuItems = computed(() =>
  menuList.value.map(item => {
    const visibleChildren = (item.children || []).filter(c => !c.meta?.isHide);
    const base = {
      key: item.path,
      label: getMenuTitle(item),
      title: getMenuTitle(item),
      icon: renderIcon(item.meta?.icon)
    };
    if (visibleChildren.length) {
      base.children = visibleChildren.map(c => ({
        key: c.path,
        label: getMenuTitle(c),
        title: getMenuTitle(c),
        icon: renderIcon(c.meta?.icon)
      }));
    }
    return base;
  })
);

const selectedKeys = computed(() => {
  const name = route.name;
  const findKey = (list, targetName) => {
    for (const item of list) {
      if (item.name === targetName) return item.path;
      if (item.children?.length) {
        const k = findKey(item.children, targetName);
        if (k) return k;
      }
    }
    return null;
  };
  const key = findKey(menuList.value, name);
  return key ? [key] : [route.path];
});

const openKeys = ref([]);
watch(
  () => route.path,
  () => {
    const path = route.path;
    for (const item of menuList.value) {
      if (item.children?.some(c => path.startsWith(c.path))) {
        openKeys.value = [item.path];
        return;
      }
    }
  },
  { immediate: true }
);

const isCollapse = computed(() => props.collapsed);

function handleClick({ key }) {
  const item = findItemByPath(menuList.value, key);
  if (item?.meta?.isLink) {
    window.open(item.meta.isLink, "_blank");
    return;
  }
  router.push(key);
}

function findItemByPath(list, path) {
  for (const item of list) {
    if (item.path === path) return item;
    if (item.children?.length) {
      const found = findItemByPath(item.children, path);
      if (found) return found;
    }
  }
  return null;
}

function handleOpenChange(keys) {
  openKeys.value = keys;
}

function toggleCollapse() {
  emit("update:collapsed", !props.collapsed);
}
</script>

<style scoped lang="scss">
.sidebar-menu-full {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;

  :deep(.ant-menu) {
    flex: 1;
    padding: 8px 0;
    overflow: visible auto;
    border-inline-end: none !important;
  }

  :deep(.ant-menu-sub) {
    background: transparent !important;
  }

  :deep(.ant-menu-sub .ant-menu-item),
  :deep(.ant-menu-item) {
    color: var(--text-primary, #1a1a1a) !important;

    .menu-item-title {
      color: inherit;
      opacity: 1;
    }
  }

  :deep(.ant-menu-title-content) {
    color: inherit !important;
  }

  .sidebar-collapse {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    height: 48px;
    cursor: pointer;
    border-top: 1px solid var(--layout-border, #f0f0f0);

    .collapse-icon {
      font-size: 18px;
      color: var(--text-secondary, #666666);
    }
  }
}
</style>
