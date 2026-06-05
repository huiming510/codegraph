<template>
  <div class="header-search" @click="openSearchBar">
    <span class="search-item"><i class="iconfont icon-search" /> 搜索</span>
    <span class="search-item"><i class="iconfont icon-commad" /> ctrl k</span>
  </div>
</template>

<script setup>
import { useShortcut } from "@/hooks/useShortcut.js";

import searchBar from "@/components/SearchBar/index.js";

const openSearchBar = () => {
  searchBar.open();
};

useShortcut(["ctrl", "k"], () => {
  openSearchBar();
});
</script>

<style scoped lang="scss">
.header-search {
  display: flex;
  gap: 15px;
  align-items: center;
  justify-content: space-around;
  min-width: 120px;
  height: 32px;
  padding: 0 10px;
  color: rgb(0 0 0 / 65%);
  cursor: pointer;
  border: 1px solid #c7def5;
  border-radius: 16px;
  white-space: nowrap;
  flex-shrink: 0;

  &:hover {
    background-color: rgb(199 222 245 / 80%);
  }
}

.search-item {
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: 14px;
  white-space: nowrap;
}
</style>
