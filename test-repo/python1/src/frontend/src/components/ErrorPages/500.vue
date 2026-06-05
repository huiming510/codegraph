<template>
  <div class="not-container">
    <img class="not-img" alt="500" src="@/assets/images/500.png" />
    <div class="not-detail">
      <h4>抱歉，您的网络不见了~🤷‍♂️🤷‍♀️</h4>
      <a-button type="primary" @click="router.back">返回上一页</a-button>
    </div>
  </div>
</template>

<script setup lang="ts" name="500">
import { useRouter } from "vue-router";
const router = useRouter();
</script>

<style scoped lang="scss">
@use "./index";
</style>
