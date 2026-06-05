# StreamMarkdown 组件

流式渲染 Markdown 内容的 Vue 3 组件，支持模拟 Server-Sent Events (SSE) 效果。

## 功能特性

- 🎯 **流式渲染**: 模拟 SSE 效果，逐个字符渲染 Markdown 内容
- 📝 **Markdown 支持**: 完整的 Markdown 语法支持，包括代码高亮、表格、列表等
- 🎨 **代码高亮**: 集成 Highlight.js，支持多种编程语言
- 📋 **复制功能**: 代码块一键复制功能
- 🔄 **动态更新**: 高效的 DOM 增量更新，避免全量重新渲染
- 🎛️ **高度可配置**: 支持自定义 SSE 参数、样式等
- 📱 **响应式设计**: 适配不同屏幕尺寸

## 安装依赖

确保项目中已安装以下依赖：

```bash
npm install markdown-it highlight.js clipboard @datatraccorporation/markdown-it-mermaid
# 以及相关插件...
```

## 基本用法

```vue
<template>
  <div class="app">
    <StreamMarkdown
      :content="markdownContent"
      :auto-start="false"
      :sse-options="sseConfig"
      @complete="onComplete"
    />
  </div>
</template>

<script setup>
import StreamMarkdown from '@/components/StreamMarkdown/index.vue';

const markdownContent = `# Hello World

这是一个 **流式渲染** 的 Markdown 示例。

\`\`\`javascript
console.log('Hello, World!');
\`\`\`

- 列表项 1
- 列表项 2
- 列表项 3
`;

const sseConfig = {
  minChunkSize: 1,
  maxChunkSize: 20,
  delay: 30
};

const onComplete = () => {
  console.log('渲染完成！');
};
</script>
```

## Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `content` | `String` | `''` | 要渲染的 Markdown 内容 |
| `autoStart` | `Boolean` | `false` | 是否自动开始流式渲染 |
| `sseOptions` | `Object` | `{minChunkSize: 1, maxChunkSize: 20, delay: 20}` | SSE 模拟配置 |
| `showHeader` | `Boolean` | `true` | 是否显示头部控制栏 |
| `showFooter` | `Boolean` | `false` | 是否显示底部插槽 |
| `contentId` | `String` | `'stream-markdown-content'` | 内容容器ID |

### sseOptions 配置

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `minChunkSize` | `Number` | `1` | 最小块大小 |
| `maxChunkSize` | `Number` | `20` | 最大块大小 |
| `delay` | `Number` | `20` | 每次渲染间隔(ms) |

## Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `start` | - | 开始流式渲染时触发 |
| `complete` | - | 流式渲染完成时触发 |
| `reset` | - | 重置时触发 |
| `error` | `error` | 错误时触发 |

## Slots

| 插槽名 | 说明 |
|--------|------|
| `header` | 自定义头部内容，默认显示开始/重置按钮 |
| `footer` | 自定义底部内容 |

## 方法

通过 `ref` 可以调用以下方法：

```javascript
const streamRef = ref(null);

// 开始流式渲染
streamRef.startStreaming();

// 重置组件
streamRef.reset();

// 获取当前是否正在渲染
console.log(streamRef.isStreaming);
```

## 自定义样式

组件提供了完整的样式定制能力：

```vue
<style scoped>
/* 自定义代码块样式 */
.stream-markdown-content :deep(.article-content pre) {
  background: #1e1e1e;
  border-radius: 8px;
}

/* 自定义按钮样式 */
.stream-markdown-header .start-btn {
  background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
}
</style>
```

## 高级用法

### 自定义 SSE 配置

```javascript
const customSSEOptions = {
  minChunkSize: 5,    // 最小每次渲染5个字符
  maxChunkSize: 50,   // 最大每次渲染50个字符
  delay: 50           // 每次渲染间隔50ms
};
```

### 监听渲染进度

```vue
<template>
  <StreamMarkdown
    ref="streamRef"
    :content="content"
    @start="onStart"
    @complete="onComplete"
    @error="onError"
  />
</template>

<script setup>
const onStart = () => {
  console.log('开始渲染...');
};

const onComplete = () => {
  console.log('渲染完成！');
  // 可以在这里执行后续操作
};

const onError = (error) => {
  console.error('渲染出错:', error);
};
</script>
```

### 自定义头部

```vue
<template>
  <StreamMarkdown :content="content">
    <template #header>
      <div class="custom-header">
        <h3>实时文档</h3>
        <button @click="customStart">开始</button>
        <button @click="customPause">暂停</button>
      </div>
    </template>
  </StreamMarkdown>
</template>
```

## 注意事项

1. **依赖安装**: 确保所有相关依赖都已正确安装
2. **内容编码**: Markdown 内容应为有效的 UTF-8 字符串
3. **性能考虑**: 超长内容可能影响渲染性能，建议适当分块
4. **样式隔离**: 组件使用了 scoped 样式，如需全局覆盖请使用 `:deep()` 选择器

## 技术实现

- **SSE 模拟**: 使用生成器函数模拟流式数据
- **增量渲染**: 实现 DOM 节点的增量更新，避免全量重绘
- **代码高亮**: 集成 Highlight.js，支持 15+ 种编程语言
- **Markdown 解析**: 使用 markdown-it，支持丰富的插件生态