<template>
  <a-layout class="layout-container" :class="{ 'header-style-dark': globalStore.theme === 'dark' }">
    <a-layout-header>
      <Header />
    </a-layout-header>
    <a-layout>
      <a-layout-sider :width="160" :collapsed-width="80" :collapsed="isCollapse" v-if="showSidebar">
        <Menu v-if="showSidebar" />
      </a-layout-sider>
      <a-layout-content :class="[showSidebar ? 'has-sider-main' : 'main-page']">
        <Main />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup name="layout">
import { ref, computed, provide } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/modules/auth";
import { useGlobalStore } from "@/stores/modules/global";

import Header from "./components/Header/index.vue";
import Menu from "./components/Sider/SubMenu.vue";
import Main from "./components/Main/index.vue";

const isCollapse = ref(false);
const globalStore = useGlobalStore();

const route = useRoute();
const authStore = useAuthStore();

// 根据当前路由和菜单列表获取 route 数据
const routeData = computed(() => {
  return findRouteWithParent(authStore.authMenuListGet, route.name);
});

// 检查是否应该显示侧边栏
const showSidebar = computed(() => {
  // 如果当前路由设置了 hideMenu，则不显示侧边栏
  if (route.meta?.hideMenu) {
    return false;
  }
  // 否则根据是否有子路由来决定
  return routeData.value?.parent?.children.filter(item => !item.meta.isHide)?.length;
});

// 查找当前路由及父路由
const findRouteWithParent = (menuList, currentName) => {
  for (let menu of menuList) {
    if (menu.name === currentName) {
      return { parent: null, current: menu, path: menu.path };
    }
    if (menu?.children?.length) {
      const result = findRouteWithParent(menu.children, currentName);
      if (result.current) {
        return { parent: menu, current: result.current, path: result.current.path };
      }
    }
  }
  return { parent: null, current: null, path: route.path };
};

provide("routeData", routeData);
provide("isCollapse", isCollapse);
</script>

<style scoped lang="scss">
@use "./index.scss";
</style>
