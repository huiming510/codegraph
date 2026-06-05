<template>
  <div class="knowledge-popover">
    <template v-for="item in addKnowledgeOptions" :key="item.title">
      <div class="knowledge-item" @click="handleItemClick(item)">
        <div class="knowledge-item-icon">
          <SvgIcon :name="item.svg" :iconStyle="{ width: '30px', height: '30px' }" />
        </div>
        <div class="knowledge-item-content">
          <div class="knowledge-item-title">{{ item.title }}</div>
          <div class="knowledge-item-desc">{{ item.desc }}</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { addKnowledgeOptions } from "@/constants/knowledge.js";
import SvgIcon from "@/components/SvgIcon/index.vue";

// 处理点击事件
const handleItemClick = item => {
  console.log("Item clicked:", item);
};
</script>

<style scoped lang="scss">
.knowledge-popover {
  .knowledge-item {
    display: flex;
    align-items: center;
    padding: 8px;
    cursor: pointer;

    &:hover {
      background-color: #f0f4ff;
      border-radius: 6px;
    }

    .knowledge-item-icon {
      width: 32px;
      height: 32px;
    }

    .knowledge-item-content {
      margin-left: 10px;

      .knowledge-item-title {
        margin-bottom: 2px;
        font-weight: 600;
      }

      .knowledge-item-desc {
        font-size: 12px;
        color: rgb(0 0 0 / 45%);
      }
    }
  }
}
</style>
