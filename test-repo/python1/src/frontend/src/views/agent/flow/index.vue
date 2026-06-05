<template>
  <div class="flow-detail">
    <Header />
    <Flow />
  </div>
</template>

<script setup>
import { watchEffect } from "vue";
import { useRoute } from "vue-router";

import Header from "./components/Header.vue";
import Flow from "./components/Flow.vue";

const route = useRoute();

watchEffect(() => {
  console.log(route.params);
});
</script>

<style scoped lang="scss">
.flow-detail {
  width: 100%;
  height: 100%;
}
</style>
