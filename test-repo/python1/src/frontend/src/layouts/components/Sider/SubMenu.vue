<template>
  <div class="layout-second-menu">
    <a-menu :selected-keys="[routePath]" :inline-collapsed="isCollapse" mode="inline">
      <a-menu-item v-for="subItem in menuList" :key="subItem.path" @click="handleClickMenu(subItem)">
        <template #icon>
          <i v-if="subItem.meta.icon" :class="['iconfont', subItem.meta.icon]" />
        </template>
        <span class="menu-title">{{ subItem.meta.title }}</span>
      </a-menu-item>
    </a-menu>
    <div class="menu-collapse">
      <MenuUnfoldOutlined v-if="isCollapse" :style="{ fontSize: '24px' }" class="collapse-icon" @click="handleChangeCollapse" />
      <MenuFoldOutlined v-else :style="{ fontSize: '24px' }" class="collapse-icon" @click="handleChangeCollapse" />
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from "vue";
import { useRouter } from "vue-router";
import { MenuUnfoldOutlined, MenuFoldOutlined } from "@ant-design/icons-vue";

const router = useRouter();
const routeData = inject("routeData");
const isCollapse = inject("isCollapse");

const menuList = computed(() => {
  return routeData.value?.parent?.children.filter(item => !item.meta.isHide);
});
const routePath = computed(() => {
  return routeData.value.current.path;
});
console.log(routePath);

const handleClickMenu = subItem => {
  if (subItem.meta.isLink) return window.open(subItem.meta.isLink, "_blank");
  router.push(subItem.path);
};

const handleChangeCollapse = () => {
  isCollapse.value = !isCollapse.value;
};
</script>

<style scoped lang="scss">
.layout-second-menu {
  height: 100%;
  border-right: 1px solid #f0f0f0;

  :deep(.ant-menu) {
    width: 100%;
    height: calc(100% - 50px);
    padding: 10px 3px;
    overflow-y: auto;
    border: 0;

    .ant-menu-submenu,
    .ant-menu-item {
      height: 45px;
      line-height: 45px;

      .iconfont {
        font-size: 18px;
        text-align: center;
      }
    }

    .ant-menu-item {
      margin-bottom: 5px;
      border-radius: 4px;

      &.ant-menu-item-selected {
        color: #1677ff !important;
        background-color: #e6f4ff !important;
      }
    }
  }

  .menu-collapse {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 50px;
    background-color: #ffffff;
    border-top: 1px solid #f0f0f0;

    .collapse-icon {
      width: 34px;
      height: 34px;
      padding: 5px;
      cursor: pointer;
      border: 1px solid #f0f0f0;
      border-radius: 5px;

      &:hover {
        color: #1677ff;
        border-color: #1677ff;
      }
    }
  }
}
</style>
