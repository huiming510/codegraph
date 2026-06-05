<template>
  <div class="layout-header">
    <div class="layout-header-left">
      <LogoArea />
      <Menu />
    </div>
    <div class="layout-header-right">
      <Search />
      <ThemeToggle />
      <LanguageSelect />
      <Avatar />
    </div>
  </div>
</template>

<script setup>
import Menu from "./Menu.vue";
import LogoArea from "./LogoArea.vue";
import Search from "./Search.vue";
import ThemeToggle from "./ThemeToggle.vue";
import LanguageSelect from "./LanguageSelect.vue";
import Avatar from "./Avatar.vue";
</script>

<style scoped lang="scss">
@use "./index";
</style>
