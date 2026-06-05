<template>
  <a-card class="control">
    <a-button type="text">
      <a-tooltip title="缩小" placement="bottom">
        <ZoomOutOutlined :style="{ fontSize: '20px' }" />
      </a-tooltip>
    </a-button>
    <a-button type="text">
      <a-tooltip title="放大" placement="bottom">
        <ZoomInOutlined :style="{ fontSize: '20px' }" />
      </a-tooltip>
    </a-button>
    <a-divider type="vertical" />
  </a-card>
</template>

<script setup>
import { ZoomOutOutlined, ZoomInOutlined } from "@ant-design/icons-vue";
</script>

<style scoped lang="scss">
.control {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 300px;

  :deep(.ant-card-body) {
    padding: 3px 5px !important;

    .ant-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 6px;

      &:hover {
        background: #e6f7ff;
      }
    }

    .ant-btn + .ant-btn {
      margin-left: 3px;
    }
  }
}
</style>
