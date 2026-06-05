<template>
  <div class="lf-container">
    <div id="lf-view" ref="lfContainerRef"></div>
    <Control />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";

import LogicFlow from "@logicflow/core";
import Control from "./Control.vue";

import "@logicflow/core/lib/style/index.css";
import "@logicflow/extension/lib/style/index.css";

// 默认配置
let config = ref({
  background: {
    backgroundColor: "#f2f3f5"
  },
  grid: {
    size: 10,
    visible: false
  },
  keyboard: {
    enabled: true
  },
  edgeType: "bezier", // 使用边 line/polyline/bezier
  adjustEdge: false, //允许调整边
  edgeSelectedOutline: true, //鼠标 hover 的时候显示边的外框
  hoverOutline: false,
  nodeTextEdit: false, //节点是否可编辑。false不可编辑
  edgeTextEdit: false, //边是否可编辑。false不可编辑
  autoExpand: false, //点拖动靠近画布边缘时是否自动扩充画布 false不扩充
  textEdit: false, //是否开启文本编辑 false不可编辑
  snapline: false, //对齐线。false不开启
  stopScrollGraph: true // 是否阻止滚动画布
});

// 测试数据
const data = {
  nodes: [
    {
      id: "1",
      type: "rect", // 节点类型为矩形
      x: 100, // 节点的 x 坐标
      y: 100, // 节点的 y 坐标
      text: "节点1" // 节点显示的文本
    },
    {
      id: "2",
      type: "circle", // 节点类型为圆形
      x: 300, // 节点的 x 坐标
      y: 500, // 节点的 y 坐标
      text: "节点2" // 节点显示的文本
    }
  ],
  edges: [
    {
      sourceNodeId: "1", // 起始节点的 ID
      targetNodeId: "2", // 目标节点的 ID
      type: "bezier", // 边的类型为折线
      text: "", // 边显示的文本
      startPoint: {
        x: 140, // 边起点的 x 坐标
        y: 100 // 边起点的 y 坐标
      },
      endPoint: {
        x: 250, // 边终点的 x 坐标
        y: 500 // 边终点的 y 坐标
      }
    }
  ]
};

const lfRef = ref(null);
const lfContainerRef = ref(null);

// 初始化 LogicFlow
const initLf = () => {
  if (lfContainerRef.value) {
    const lf = new LogicFlow({
      ...config.value,
      container: lfContainerRef.value
    });
    lfRef.value = lf;
    initTheme();
    lfRef.value.render(data);
    lfRef.value.translateCenter();
  }
};

// 设置默认主题
const initTheme = () => {
  lfRef.value.setTheme({
    bezier: {
      stroke: "#3370ff",
      strokeWidth: 2
    }
  });
};

onMounted(() => {
  initLf();
});

onUnmounted(() => {
  lfRef.value.destroy();
});
</script>

<style scoped lang="scss">
.lf-container {
  position: relative;
  width: 100%;
  height: calc(100% - 60px);
  overflow: hidden;

  #lf-view {
    width: 100%;
    height: 100%;
    outline: none;
  }
}
</style>
