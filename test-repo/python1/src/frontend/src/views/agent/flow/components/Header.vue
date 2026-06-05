<template>
  <div class="flow-header">
    <div class="header-left">
      <i class="iconfont icon-goback" @click="goBack" />
      <div class="header-info">
        <img class="logo" src="@/assets/images/logo.png" alt="Logo" />
        <div class="info-title">
          <div class="info-name">测试</div>
          <div class="save-time">自动保存 2025 03-17 16:41</div>
        </div>
      </div>
    </div>
    <div class="header-right">
      <a-button
        v-for="button in buttons"
        :key="button.label"
        :type="button.type || 'default'"
        :ghost="button.plain"
        @click="button.action"
      >
        <i :class="button.icon" />
        {{ button.label }}
      </a-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";

const router = useRouter();

const goBack = () => {
  router.back();
};

const buttons = [
  {
    label: "编辑信息",
    icon: "iconfont icon-edit",
    type: "",
    plain: false,
    action: () => console.log("历史版本点击")
  },
  {
    label: "历史版本",
    icon: "iconfont icon-history-version",
    type: "",
    plain: false,
    action: () => console.log("历史版本点击")
  },
  {
    label: "测试日志",
    icon: "iconfont icon-log",
    type: "",
    plain: false,
    action: () => console.log("测试日志点击")
  },
  {
    label: "试运行",
    icon: "iconfont icon-run",
    type: "",
    plain: false,
    action: () => console.log("试运行点击")
  },
  {
    label: "发布",
    icon: "iconfont icon-release",
    type: "primary",
    plain: false,
    action: () => console.log("发布点击")
  }
];
</script>

<style scoped lang="scss">
.flow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 10px;
  font-size: 14px;
  border-bottom: 1px solid #f0f0f0;

  .header-left,
  .header-right {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .icon-goback {
    padding: 8px;
    font-size: 20px;
    cursor: pointer;
    border-radius: 6px;

    &:hover {
      background-color: #e6f7ff;
    }
  }

  .header-info {
    display: flex;
    gap: 10px;
    align-items: center;

    .logo {
      width: 32px;
      height: 32px;
    }

    .info-title {
      display: flex;
      flex-direction: column;
      gap: 2px;

      .info-name {
        font-size: 16px;
        font-weight: 600;
      }

      .save-time {
        padding: 1px 3px;
        font-size: 12px;
        color: rgb(0 0 0 / 65%);
        background-color: #fafafa;
        border-radius: 4px;
      }
    }
  }

  .header-right {
    .ant-btn i {
      margin-right: 5px;
    }
  }
}
</style>
