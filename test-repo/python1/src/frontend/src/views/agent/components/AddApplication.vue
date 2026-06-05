<template>
  <div class="application-popover">
    <template v-for="item in addApplicationOptions" :key="item.title">
      <div class="application-item" @click="handleItemClick(item)">
        <div class="application-item-icon">
          <SvgIcon :name="item.svg" :iconStyle="{ width: '30px', height: '30px' }" />
        </div>
        <div class="application-item-content">
          <div class="application-item-title">{{ item.title }}</div>
          <div class="application-item-desc">{{ item.desc }}</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { addApplicationOptions } from "@/constants/application.js";
import SvgIcon from "@/components/SvgIcon/index.vue";

// 处理点击事件
const handleItemClick = item => {
  console.log("Item clicked:", item);
};
</script>

<style scoped lang="scss">
.application-popover {
  .application-item {
    display: flex;
    align-items: center;
    padding: 8px;
    cursor: pointer;

    &:hover {
      background-color: #f0f4ff;
      border-radius: 6px;
    }

    .application-item-icon {
      width: 32px;
      height: 32px;
    }

    .application-item-content {
      margin-left: 10px;

      .application-item-title {
        margin-bottom: 2px;
        font-weight: 600;
      }

      .application-item-desc {
        font-size: 12px;
        color: rgb(0 0 0 / 45%);
      }
    }
  }
}
</style>
