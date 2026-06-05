<template>
  <a-form size="large" ref="loginFormRef" :model="loginForm" :rules="loginRules" layout="vertical">
    <a-form-item name="username">
      <a-input v-model:value="loginForm.username" placeholder="请输入用户名" allow-clear :prefix-hoverable="false">
        <template #prefix>
          <UserOutlined />
        </template>
      </a-input>
    </a-form-item>
    <a-form-item name="password">
      <a-input-password v-model:value="loginForm.password" placeholder="请输入密码" allow-clear :prefix-hoverable="false">
        <template #prefix>
          <LockOutlined />
        </template>
      </a-input-password>
    </a-form-item>

    <!-- 注册表单额外字段 -->
    <template v-if="isRegister">
      <a-form-item name="nickname">
        <a-input v-model:value="loginForm.nickname" placeholder="请输入昵称（可选）" allow-clear>
          <template #prefix>
            <SmileOutlined />
          </template>
        </a-input>
      </a-form-item>
      <a-form-item name="email">
        <a-input v-model:value="loginForm.email" placeholder="请输入邮箱（可选）" allow-clear>
          <template #prefix>
            <MailOutlined />
          </template>
        </a-input>
      </a-form-item>
    </template>

    <a-form-item>
      <a-button class="login-btn" size="large" type="primary" :loading="loading" block @click="handleSubmit(loginFormRef)">
        {{ loading ? (isRegister ? "注册中..." : "登录中...") : isRegister ? "注 册" : "登 录" }}
      </a-button>
    </a-form-item>

    <!-- 切换登录/注册 -->
    <div class="login-switch">
      <span v-if="!isRegister"> 没有账号？<a @click="isRegister = true">立即注册</a> </span>
      <span v-else> 已有账号？<a @click="isRegister = false">立即登录</a> </span>
    </div>

    <!-- 默认账号提示 -->
    <div class="login-tips">
      <a-divider style="margin: 16px 0; font-size: 12px; color: #bfbfbf">默认账号</a-divider>
      <div class="tips-content">管理员：admin / admin123</div>
    </div>
  </a-form>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import { UserOutlined, LockOutlined, SmileOutlined, MailOutlined } from "@ant-design/icons-vue";
import { useUserStore } from "@/stores/modules/user";
import { login, register } from "@/api/modules/login";
import { initDynamicRouters } from "@/router/modules/dynamicRouter";

const router = useRouter();
const userStore = useUserStore();

const loginFormRef = ref();
const isRegister = ref(false);

const loginRules = ref({
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }]
});

const loading = ref(false);
const loginForm = ref({
  username: "admin",
  password: "admin123",
  nickname: "",
  email: ""
});

// 登录/注册
const handleSubmit = async formEl => {
  if (!formEl) return;
  await formEl.validate();

  loading.value = true;
  try {
    const params = {
      username: loginForm.value.username,
      password: loginForm.value.password,
      ...(isRegister.value && {
        nickname: loginForm.value.nickname,
        email: loginForm.value.email
      })
    };
    const data = isRegister.value ? await register(params) : await login(params);

    message.success(isRegister.value ? "注册成功！" : "登录成功！");
    userStore.setToken(data?.access_token ?? "");
    userStore.setUserInfo(data?.user ?? null);

    await initDynamicRouters();
    router.push("/home");
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped lang="scss">
.login-switch {
  margin-bottom: 16px;
  color: #8c8c8c;
  text-align: center;

  a {
    color: #667eea;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
}

.login-tips {
  .tips-content {
    font-size: 12px;
    color: #bfbfbf;
    text-align: center;
  }
}
</style>
