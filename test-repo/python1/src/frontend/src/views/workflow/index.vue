<template>
  <div class="workflow-page">
    <a-card :bordered="false" class="intro-card">
      <p class="intro-text">处理文档流程</p>
    </a-card>
  </div>
</template>

<script setup name="workflow"></script>

<style scoped lang="scss">
.workflow-page {
  padding: 24px;
  min-height: 400px;
}
.intro-card {
  max-width: 640px;
  margin: 0 auto;
}
.intro-text {
  margin: 0;
  font-size: 16px;
  line-height: 1.8;
  color: rgba(0, 0, 0, 0.85);
}
</style>
