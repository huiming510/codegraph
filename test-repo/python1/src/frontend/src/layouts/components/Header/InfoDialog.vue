<template>
  <a-modal v-model:open="dialogVisible" title="个人信息" :width="500">
    <span>This is userInfo</span>
    <template #footer>
      <a-button @click="dialogVisible = false">取消</a-button>
      <a-button type="primary" @click="dialogVisible = false">确认</a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref } from "vue";

const dialogVisible = ref(false);
const openDialog = () => {
  dialogVisible.value = true;
};

defineExpose({ openDialog });
</script>
