<template>
  <a-menu class="header-menu" :selected-keys="[routePath]" mode="horizontal">
    <template v-for="menu in menuList" :key="menu.path || menu.groupTitle || menu.id">
      <a-menu-item @click="() => handleClickMenu(menu)">
        {{ menu.meta.title }}
      </a-menu-item>
    </template>
  </a-menu>
</template>

<script setup>
import { computed, inject } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/modules/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const routeData = inject("routeData");

// 直接使用 authStore.authMenuListGet，按 groupTitle 分组处理
const menuList = computed(() => {
  const menuData = authStore.authMenuListGet || [];
  return menuData;
});

const routePath = computed(() => {
  return (routeData.value?.parent?.path || routeData.value?.current?.path) ?? route.path;
});

const handleClickMenu = menu => {
  if (route.name === menu.name) return;
  if (menu.meta?.isLink) {
    window.open(menu.meta.isLink, "_blank");
    return;
  }
  router.push(menu.path);
};
</script>

<style scoped lang="scss">
.header-menu {
  height: 60px;
  font-size: 15px;
  font-weight: bold;
  background-color: transparent;
  border: 0;

  :deep(.ant-menu-item) {
    margin-top: -2px;

    &::after,
    &:hover::after {
      border-bottom-width: 4px;
    }
  }
}
</style>
