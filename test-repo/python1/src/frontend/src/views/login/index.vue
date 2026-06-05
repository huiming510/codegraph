<template>
  <div class="login-container select-none">
    <img class="login-bg" src="@/assets/images/login_bg.png" />
    <div class="login-bg-overlay" />
    <div class="login-bg-decoration">
      <div class="decoration-circle decoration-circle-1" />
      <div class="decoration-circle decoration-circle-2" />
      <div class="decoration-circle decoration-circle-3" />
    </div>
    <div class="login-box">
      <div class="login-box-left">
        <div class="login-illustration">
          <SvgIcon name="loginleft" :iconStyle="{ width: '700px', height: '450px' }" />
        </div>
      </div>
      <div class="login-box-right">
        <div class="login-form">
          <div class="login-form-header">
            <div class="login-form-header-top">
              <img class="login-form-header-logo" src="@/assets/images/logo.png" />
              <h2 class="login-form-header-title">{{ appTitle }}</h2>
            </div>
            <p class="login-form-header-subtitle">欢迎回来，请登录您的账户</p>
          </div>
          <LoginForm />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup name="login">
import SvgIcon from "@/components/SvgIcon/index.vue";
import LoginForm from "./components/LoginForm.vue";

const appTitle = import.meta.env.VITE_APP_TITLE;
</script>

<style scoped lang="scss">
@use "./index";
</style>
