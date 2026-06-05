<template>
  <router-view v-slot="{ Component, route }">
    <!-- <transition appear name="fade-transform" mode="out-in"> -->
    <component :is="Component" :key="route.fullPath" />
    <!-- </transition> -->
  </router-view>
</template>

<script setup></script>

<style scoped lang="scss"></style>
