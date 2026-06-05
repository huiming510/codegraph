<template>
  <a-dropdown :trigger="['click']">
    <div class="user-info">
      <div class="user-info-avatar">
        <img src="@/assets/images/avatar.png" alt="avatar" />
      </div>
      <span class="user-info-name">{{ userStore.userInfo?.username }}</span>
      <DownOutlined />
    </div>
    <template #overlay>
      <a-menu>
        <a-menu-item @click="openDialog('infoRef')">
          <template #icon>
            <UserOutlined />
          </template>
          个人信息
        </a-menu-item>
        <a-menu-item @click="openDialog('passwordRef')">
          <template #icon>
            <EditOutlined />
          </template>
          修改密码
        </a-menu-item>
        <a-menu-divider />
        <a-menu-item @click="logout">
          <template #icon>
            <LogoutOutlined />
          </template>
          退出登录
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
  <!-- infoDialog -->
  <InfoDialog ref="infoRef"></InfoDialog>
  <!-- passwordDialog -->
  <PasswordDialog ref="passwordRef"></PasswordDialog>
</template>

<script setup>
import { ref } from "vue";
import { LOGIN_URL } from "@/constants/router";
import { useRouter } from "vue-router";
import { logout as logoutApi } from "@/api/modules/login";
import { useUserStore } from "@/stores/modules/user";
import { useAuthStore } from "@/stores/modules/auth";
import { resetRouter } from "@/router";
import { Modal, message } from "ant-design-vue";
import { DownOutlined, UserOutlined, EditOutlined, LogoutOutlined } from "@ant-design/icons-vue";
import InfoDialog from "./InfoDialog.vue";
import PasswordDialog from "./PasswordDialog.vue";

const router = useRouter();
const userStore = useUserStore();
const authStore = useAuthStore();

// 退出登录
const logout = () => {
  Modal.confirm({
    title: "温馨提示",
    content: "您是否确认退出登录?",
    okText: "确定",
    cancelText: "取消",
    onOk: async () => {
      // 1.执行退出登录接口
      await logoutApi();

      // 2.先按当前菜单移除动态路由，再清空菜单和 Token，避免换账号登录时路由错乱/404
      resetRouter();
      authStore.clearMenuList();
      userStore.logout();

      // 3.重定向到登陆页
      router.replace(LOGIN_URL);
      message.success("退出登录成功！");
    }
  });
};

// 打开修改密码和个人信息弹窗
const infoRef = ref(null);
const passwordRef = ref(null);
const openDialog = ref => {
  if (ref == "infoRef") infoRef.value?.openDialog();
  if (ref == "passwordRef") passwordRef.value?.openDialog();
};
</script>

<style scoped lang="scss">
.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;

  &-name {
    margin: 0 5px 0 7px;
    font-size: 16px;
    font-weight: bold;
  }

  &-avatar {
    width: 32px;
    height: 32px;
    overflow: hidden;
    border-radius: 50%;

    img {
      width: 100%;
      height: 100%;
      vertical-align: top;
    }
  }
}
</style>
