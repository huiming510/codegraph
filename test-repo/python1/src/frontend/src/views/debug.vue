<template>
  <div style="padding: 20px">
    <h2>调试信息</h2>
    <a-card title="用户信息" style="margin-bottom: 20px">
      <p><strong>Token:</strong> {{ userStore.token ? "已设置" : "未设置" }}</p>
      <p><strong>用户信息:</strong></p>
      <pre>{{ JSON.stringify(userStore.userInfo, null, 2) }}</pre>
      <p><strong>是否管理员:</strong> {{ userStore.isAdmin }}</p>
      <p><strong>角色:</strong> {{ userStore.role }}</p>
    </a-card>

    <a-card title="菜单信息">
      <p><strong>菜单数量:</strong> {{ authStore.authMenuListGet.length }}</p>
      <p><strong>菜单列表:</strong></p>
      <pre>{{ JSON.stringify(authStore.authMenuListGet, null, 2) }}</pre>
    </a-card>

    <a-button type="primary" @click="refreshMenu" style="margin-top: 20px"> 刷新菜单 </a-button>
  </div>
</template>

<script setup>
import { useUserStore } from "@/stores/modules/user";
import { useAuthStore } from "@/stores/modules/auth";

const userStore = useUserStore();
const authStore = useAuthStore();

const refreshMenu = async () => {
  await authStore.getMenuList();
  console.log("菜单已刷新");
};
</script>
