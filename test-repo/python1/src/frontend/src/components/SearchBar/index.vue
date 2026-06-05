<template>
  <Transition name="search-bar">
    <div v-if="isOpen" class="search-bar-container">
      <div class="search-bar">
        <div class="search-bar-input">
          <a-input v-model:value="searchQuery" size="large" placeholder="请输入搜索内容..." allow-clear>
            <template #prefix>
              <SearchOutlined />
            </template>
          </a-input>
        </div>
        <div class="search-scrollbar">
          <div v-if="searchHistory.length && !searchResults.length" class="search-history">
            <div class="history-title">搜索历史</div>
            <div v-for="(item, index) in searchHistory" :key="index" class="history-item">
              {{ item }}
            </div>
          </div>
          <div v-else-if="searchResults.length" class="search-content">
            <a-card v-for="(item, index) in searchResults" :key="index" class="result-item" :bordered="false" size="small">
              <div>
                <span></span>
                <span>{{ item }}</span>
              </div>
            </a-card>
          </div>
          <div v-if="!searchResults.length && !searchHistory.length" class="empty-state">没有相关内容</div>
        </div>
        <div class="search-bar-footer">
          <span><i class="iconfont icon-enter" />选择</span>
          <span><i class="iconfont icon-esc" />退出</span>
          <span><i class="iconfont icon-upper" />向上</span>
          <span><i class="iconfont icon-down" />向下</span>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import { SearchOutlined } from "@ant-design/icons-vue";
import { Card as ACard, Input as AInput } from "ant-design-vue";
import { useShortcut } from "@/hooks/useShortcut.js";
import searchBar from "./index.js";

const searchQuery = ref("");
const searchResults = ref([
  "搜索结果 1",
  "搜索结果 2",
  "搜索结果 3",
  "搜索结果 1",
  "搜索结果 2",
  "搜索结果 3",
  "搜索结果 1",
  "搜索结果 2",
  "搜索结果 3"
]); // 示例数据
const searchHistory = ref(["历史记录 1", "历史记录 2", "历史记录 2", "历史记录 2", "历史记录 2", "历史记录 2", "历史记录 2"]); // 示例数据
const isOpen = ref(false); // 控制搜索框显示/隐藏

const handleClickOutside = event => {
  if (!isOpen.value) return;
  if (!event.target.closest(".search-bar")) {
    closeSearchBar();
  }
};

const openSearchBar = () => {
  searchBar.open();
  isOpen.value = true;

  nextTick(() => {
    setTimeout(() => {
      document.addEventListener("click", handleClickOutside);
    }, 100);
  });
};

const closeSearchBar = () => {
  isOpen.value = false;

  setTimeout(() => {
    searchBar.close();
    document.removeEventListener("click", handleClickOutside);
  }, 300); // 确保动画完成后再移除
};

useShortcut("Enter", () => {
  console.log("1");
});
useShortcut("Escape", () => {
  console.log("2");
});
useShortcut("ArrowUp", () => {
  console.log("向上箭头触发");
});
useShortcut("ArrowDown", () => {
  console.log("向下箭头触发");
});

onMounted(() => {
  document.addEventListener("openSearch", openSearchBar);
  document.addEventListener("closeSearch", closeSearchBar);
});

onBeforeUnmount(() => {
  document.removeEventListener("openSearch", openSearchBar);
  document.removeEventListener("closeSearch", closeSearchBar);
});
</script>

<style scoped lang="scss">
@use "./index.scss";

/* Vue Transition 动画 */
.search-bar-enter-active,
.search-bar-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}

.search-bar-enter-from,
.search-bar-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
