<template>
  <div class="stream-markdown">
    <div class="stream-markdown-header" v-if="showHeader">
      <slot name="header">
        <div class="default-header">
          <button class="start-btn" @click="startStreaming" :disabled="isStreaming">
            {{ isStreaming ? "流式渲染中..." : "开始流式渲染" }}
          </button>
          <button class="reset-btn" @click="reset" :disabled="isStreaming">重置</button>
        </div>
      </slot>
    </div>

    <div class="stream-markdown-content">
      <div class="article-content" :id="contentId" ref="contentRef"></div>
    </div>

    <div class="stream-markdown-footer" v-if="showFooter">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
/**
 * StreamMarkdown 组件
 * 用于流式渲染 Markdown 内容的组件
 */

import { ref, nextTick, onMounted, onUnmounted, watch } from "vue";
import markdownIt from "./modules/markdown-it";
import { buildCodeBlock, deepCloneAndUpdate } from "./modules/code-block";
import { startSSESimulation } from "./modules/sse-simulator";

// Props 定义
const props = defineProps({
  // 要渲染的 Markdown 内容
  content: {
    type: String,
    default: ""
  },
  // 是否自动开始流式渲染
  autoStart: {
    type: Boolean,
    default: false
  },
  // 是否启用内容变化时的自动流式渲染
  autoStreamOnChange: {
    type: Boolean,
    default: true
  },
  // 是否已完成流式渲染（用于控制markdown渲染时机）
  isStreamComplete: {
    type: Boolean,
    default: false
  },
  // SSE 配置选项
  sseOptions: {
    type: Object,
    default: () => ({
      minChunkSize: 1,
      maxChunkSize: 20,
      delay: 20
    })
  },
  // 是否显示头部
  showHeader: {
    type: Boolean,
    default: true
  },
  // 是否显示底部
  showFooter: {
    type: Boolean,
    default: false
  },
  // 内容容器ID
  contentId: {
    type: String,
    default: "stream-markdown-content"
  }
});

// Emits 定义
const emit = defineEmits([
  "start", // 开始流式渲染时触发
  "complete", // 流式渲染完成时触发
  "reset", // 重置时触发
  "error" // 错误时触发
]);

// 响应式数据
const contentRef = ref(null);
const htmlData = ref("");
const isStreaming = ref(false);
const renderQueue = ref([]);
const isRendering = ref(false);
const markdownItInstance = ref(null);

// 初始化 markdown-it 实例
const initMarkdownIt = async () => {
  if (!markdownItInstance.value) {
    markdownItInstance.value = await markdownIt();
  }
  return markdownItInstance.value;
};

// 渲染 Markdown 的 HTML Element
const renderMarkdown = async data => {
  if (!contentRef.value) return;

  const md = await initMarkdownIt();
  const tmpDiv = document.createElement("div");
  tmpDiv.innerHTML = md.render(data); // 只渲染当前的块
  buildCodeBlock(tmpDiv);

  // 这里不再拼接 htmlData，而是每次渲染独立的块
  deepCloneAndUpdate(contentRef.value, tmpDiv);
};

// 异步队列控制渲染
const processRenderQueue = async () => {
  if (renderQueue.value.length === 0) {
    isRendering.value = false; // 队列为空时标记渲染完成
    return;
  }

  const data = renderQueue.value.shift(); // 获取并移除队列中的第一个渲染任务
  await renderMarkdown(data); // 执行渲染操作

  // 继续处理下一个渲染任务
  setTimeout(processRenderQueue, 0);
};

// 异步队列控制渲染
const enqueueRender = data => {
  htmlData.value += data;
  renderQueue.value.push(htmlData.value);
  // 如果当前没有渲染任务在进行，启动渲染队列
  if (!isRendering.value) {
    isRendering.value = true;
    processRenderQueue();
  }
};

// 开始流式渲染
const startStreaming = () => {
  if (!props.content || isStreaming.value) return;

  // 重置状态
  reset();

  isStreaming.value = true;
  emit("start");

  // 开始 SSE 模拟
  startSSESimulation(props.content, props.sseOptions, {
    onContent: chunk => {
      enqueueRender(chunk);
    },
    onComplete: () => {
      isStreaming.value = false;
      emit("complete");
    },
    onError: error => {
      isStreaming.value = false;
      emit("error", error);
    }
  });
};

// 重置组件状态
const reset = () => {
  htmlData.value = "";
  renderQueue.value = [];
  isRendering.value = false;

  if (contentRef.value) {
    contentRef.value.innerHTML = "";
  }

  emit("reset");
};

// 暴露方法给父组件
defineExpose({
  startStreaming,
  reset,
  isStreaming,
  renderMarkdown
});

// 监听 content 变化，在启用自动流式渲染时处理
watch(
  () => props.content,
  async (newContent, oldContent) => {
    // 只有在启用自动流式渲染且不显示头部按钮时才自动处理
    if (props.autoStreamOnChange && !props.showHeader && newContent && newContent !== oldContent) {
      if (contentRef.value) {
        // 如果流式渲染已完成，进行完整的markdown渲染
        if (props.isStreamComplete && !isStreaming.value) {
          try {
            await renderMarkdown(newContent);
          } catch (error) {
            console.warn("完整渲染失败:", error);
            // 降级到纯文本显示
            contentRef.value.textContent = newContent;
          }
        }
        // 如果流式渲染进行中，直接显示文本
        else {
          contentRef.value.textContent = newContent;
        }
      }
    }
  },
  { immediate: false }
);

// 监听流式渲染完成状态
watch(
  () => props.isStreamComplete,
  async newComplete => {
    if (newComplete && props.content && !isStreaming.value) {
      // 流式渲染完成后，进行完整的markdown渲染
      try {
        await renderMarkdown(props.content);
      } catch (error) {
        console.warn("完成后的markdown渲染失败:", error);
      }
    }
  }
);

// 生命周期
onMounted(() => {
  if (props.autoStart && props.content) {
    nextTick(() => {
      startStreaming();
    });
  }
});
</script>

<style scoped lang="scss">
.stream-markdown {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.stream-markdown-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;

  .default-header {
    display: flex;
    gap: 12px;

    button {
      padding: 6px 16px;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      background: #fff;
      color: #666;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.3s ease;

      &:hover:not(:disabled) {
        border-color: #1890ff;
        color: #1890ff;
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }

    .start-btn {
      background: #1890ff;
      border-color: #1890ff;
      color: #fff;

      &:hover:not(:disabled) {
        background: #40a9ff;
        border-color: #40a9ff;
      }
    }
  }
}

.stream-markdown-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;

  .article-content {
    min-height: 200px;
    font-size: 14px;
    line-height: 1.6;

    // 代码块样式
    :deep(pre) {
      position: relative;
      background: #282c34;
      border-radius: 6px;
      padding: 16px;
      margin: 16px 0;
      overflow-x: auto;

      code {
        background: transparent;
        color: #fff;
        font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
        font-size: 13px;
        line-height: 1.4;
      }

      .copy {
        position: absolute;
        top: 8px;
        right: 8px;
        padding: 4px 8px;
        background: #1890ff;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.3s ease;

        &:hover {
          background: #40a9ff;
        }

        &.copyed {
          background: #52c41a;
        }
      }
    }

    // 其他Markdown元素样式
    :deep(h1),
    :deep(h2),
    :deep(h3),
    :deep(h4),
    :deep(h5),
    :deep(h6) {
      margin: 24px 0 16px 0;
      font-weight: 600;
      color: #262626;
    }

    :deep(h1) {
      font-size: 24px;
      border-bottom: 2px solid #f0f0f0;
      padding-bottom: 8px;
    }
    :deep(h2) {
      font-size: 20px;
      border-bottom: 1px solid #f0f0f0;
      padding-bottom: 6px;
    }
    :deep(h3) {
      font-size: 18px;
    }
    :deep(h4) {
      font-size: 16px;
    }
    :deep(h5) {
      font-size: 14px;
    }
    :deep(h6) {
      font-size: 13px;
      color: #8c8c8c;
    }

    :deep(p) {
      margin: 12px 0;
      color: #595959;
    }

    :deep(ul),
    :deep(ol) {
      margin: 16px 0;
      padding-left: 24px;
    }

    :deep(li) {
      margin: 8px 0;
      color: #595959;
    }

    :deep(blockquote) {
      margin: 16px 0;
      padding: 12px 16px;
      border-left: 4px solid #1890ff;
      background: #f6ffed;
      color: #262626;
    }

    :deep(table) {
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;

      th,
      td {
        padding: 8px 12px;
        border: 1px solid #f0f0f0;
        text-align: left;
      }

      th {
        background: #fafafa;
        font-weight: 600;
      }
    }

    :deep(a) {
      color: #1890ff;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }
}

.stream-markdown-footer {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}
</style>
