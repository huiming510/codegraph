<template>
  <div class="application-container">
    <Header />
    <a-layout-content>
      <List />
    </a-layout-content>
  </div>
</template>

<script setup name="application">
import Header from "./components/Header.vue";
import List from "./components/List.vue";
</script>

<style scoped lang="scss">
@use "./index.scss";
</style>
