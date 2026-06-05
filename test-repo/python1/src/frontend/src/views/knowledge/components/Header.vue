<template>
  <div class="knowledge-header">
    <div class="knowledge-header-left">
      <a-form layout="inline" :model="knowledgeQueryForm">
        <a-form-item>
          <a-input v-model:value="knowledgeQueryForm.knowledgeName" placeholder="按名称搜索" allow-clear style="width: 200px">
            <template #prefix>
              <SearchOutlined />
            </template>
          </a-input>
        </a-form-item>
        <a-form-item>
          <a-select
            v-model:value="knowledgeQueryForm.knowledgeType"
            placeholder="按类型搜索"
            mode="multiple"
            allow-clear
            style="width: 200px"
          >
            <a-select-option v-for="item in selectTypeOptions" :key="item.value" :value="item.value">{{
              item.label
            }}</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </div>
    <div class="knowledge-header-right">
      <a-popover :overlay-style="{ borderRadius: '10px' }" placement="bottomLeft" :width="280" trigger="click">
        <template #content>
          <AddKnowledge />
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
import { useRouter } from "vue-router";
import { SearchOutlined } from "@ant-design/icons-vue";
import AddKnowledge from "./AddKnowledge.vue";

const router = useRouter();

// 搜索表单数据
const knowledgeQueryForm = ref({
  knowledgeName: "",
  knowledgeType: []
});

// 下拉选项
const selectTypeOptions = [
  { label: "文档知识库", value: "1" },
  { label: "API知识库", value: "2" }
];

// 新建按钮点击事件
const handleCreate = () => {
  console.log("新建按钮点击");
  router.push("/knowledge/upload");
};
</script>

<style scoped lang="scss">
.knowledge-header {
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
