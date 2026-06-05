<template>
  <div class="app-header">
    <div class="app-header-left">
      <a-form layout="inline" :model="appQueryForm" ref="appQueryFormRef">
        <a-form-item>
          <a-input v-model:value="appQueryForm.appName" placeholder="按名称搜索" allow-clear style="width: 150px">
            <template #prefix>
              <SearchOutlined />
            </template>
          </a-input>
        </a-form-item>
        <a-form-item>
          <a-select
            v-model:value="appQueryForm.appType"
            placeholder="按类型搜索"
            mode="multiple"
            :maxTagCount="1"
            allow-clear
            style="width: 150px"
          >
            <a-select-option v-for="item in selectTypeOptions" :key="item.value" :value="item.value">{{
              item.label
            }}</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </div>
    <div class="app-header-right">
      <a-popover :overlay-style="{ borderRadius: '10px' }" placement="bottomLeft" :width="280" trigger="click">
        <template #content>
          <AddApplication />
        </template>
        <a-button type="primary" @click="handleCreate">
          <i class="iconfont icon-add" />
          新建
        </a-button>
      </a-popover>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { SearchOutlined } from "@ant-design/icons-vue";
import AddApplication from "./AddApplication.vue";

// 搜索表单数据
const appQueryForm = ref({
  appName: "",
  appType: []
});

// 下拉选项
const selectTypeOptions = [
  { label: "简易配置", value: "1" },
  { label: "高级编排", value: "2" },
  { label: "插件", value: "3" }
];

// 新建按钮点击事件
const handleCreate = () => {
  console.log("新建按钮点击");
};
</script>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 0;
  margin-bottom: 15px;

  &-left {
    .ant-form {
      display: flex;
      gap: 20px;
    }
  }

  &-right {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: flex-end;

    .iconfont {
      margin-right: 5px;
    }
  }
}
</style>
