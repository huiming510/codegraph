<template>
  <div class="logo-area" @click="toHomePage">
    <img class="logo-area-img" src="@/assets/images/logo.png" />
    <div class="logo-area-title">{{ appTitle }}</div>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { HOEM_URL } from "@/constants/router";

const router = useRouter();
const appTitle = import.meta.env.VITE_APP_TITLE;

const toHomePage = () => {
  router.push(HOEM_URL);
};
</script>

<style scoped lang="scss">
.logo-area {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 60px;
  cursor: pointer;

  &-img {
    width: 36px;
    height: 36px;
  }

  &-title {
    margin-left: 8px;
    font-size: 26px;
    font-weight: bold;
    color: transparent;
    background: linear-gradient(to bottom, #6166f5 40%, #7b59e1 60%, #9343cb 100%);
    background-clip: text;
  }
}
</style>
