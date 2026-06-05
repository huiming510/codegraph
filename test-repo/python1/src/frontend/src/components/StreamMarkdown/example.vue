<template>
  <div class="stream-markdown-example">
    <h1>StreamMarkdown 组件示例</h1>

    <div class="example-controls">
      <div class="control-group">
        <label>选择示例内容：</label>
        <a-select v-model:value="selectedExample" @change="onExampleChange" style="width: 200px">
          <a-select-option value="basic">基础 Markdown</a-select-option>
          <a-select-option value="code">代码示例</a-select-option>
          <a-select-option value="complex">复杂文档</a-select-option>
        </a-select>
      </div>

      <div class="control-group">
        <label>SSE 配置：</label>
        <div class="sse-config">
          <span>块大小:</span>
          <a-input-number v-model:value="sseConfig.minChunkSize" :min="1" :max="10" size="small" />
          <span>-</span>
          <a-input-number v-model:value="sseConfig.maxChunkSize" :min="10" :max="100" size="small" />
          <span>延迟:</span>
          <a-input-number v-model:value="sseConfig.delay" :min="10" :max="200" :step="10" size="small" />
          <span>ms</span>
        </div>
      </div>
    </div>

    <div class="example-content">
      <StreamMarkdown
        ref="streamRef"
        :content="currentContent"
        :auto-start="false"
        :sse-options="sseConfig"
        @start="onStreamStart"
        @complete="onStreamComplete"
        @error="onStreamError"
      />
    </div>

    <div class="example-info">
      <a-alert
        :message="`渲染状态: ${streamStatus}`"
        :type="streamStatus === '完成' ? 'success' : streamStatus === '进行中' ? 'info' : 'warning'"
        show-icon
        style="margin-bottom: 16px"
      />

      <div class="action-buttons">
        <a-button type="primary" @click="startStreaming" :disabled="isStreaming"> 开始流式渲染 </a-button>
        <a-button @click="resetStream" :disabled="isStreaming"> 重置 </a-button>
        <a-button @click="toggleAutoStart"> {{ autoStart ? "关闭" : "开启" }}自动开始 </a-button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * StreamMarkdown 组件使用示例
 */

import { ref, computed, watch } from "vue";
import { message } from "ant-design-vue";
import StreamMarkdown from "./index.vue";

// 示例内容
const examples = {
  basic: `# 基础 Markdown 示例

这是一个 **流式渲染** 的 Markdown 演示。

## 特性列表

- ✅ 实时流式渲染
- ✅ 完整的 Markdown 支持
- ✅ 代码语法高亮
- ✅ 一键复制功能

## 表格示例

| 功能 | 状态 | 说明 |
|------|------|------|
| 流式渲染 | ✅ | 支持字符级流式输出 |
| 代码高亮 | ✅ | 集成 Highlight.js |
| 复制功能 | ✅ | 代码块一键复制 |

> **提示**: 这是一个动态渲染的示例，内容会逐个字符显示出来。
`,

  code: `# 代码示例

以下是一些编程语言的代码示例：

## JavaScript

\`\`\`javascript
// 异步函数示例
async function fetchData(url) {
  try {
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('获取数据失败:', error);
    throw error;
  }
}

// 使用示例
const apiUrl = 'https://api.example.com/data';
fetchData(apiUrl)
  .then(data => console.log(data))
  .catch(error => console.error(error));
\`\`\`

## Python

\`\`\`python
def fibonacci(n):
    """生成斐波那契数列"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# 测试
print(fibonacci(10))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
\`\`\`

## SQL

\`\`\`sql
-- 创建用户表
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 插入测试数据
INSERT INTO users (username, email) VALUES
('alice', 'alice@example.com'),
('bob', 'bob@example.com'),
('charlie', 'charlie@example.com');

-- 查询活跃用户
SELECT username, email, created_at
FROM users
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY created_at DESC;
\`\`\`
`,

  complex: `# 复杂文档示例

## 项目架构图

\`\`\`mermaid
graph TB
    A[前端 Vue.js] --> B[API 网关]
    B --> C[用户服务]
    B --> D[文档服务]
    B --> E[检索服务]

    C --> F[(用户数据库)]
    D --> G[(文档数据库)]
    E --> H[(向量数据库)]

    I[LLM 服务] --> E
    J[嵌入模型] --> E
\`\`\`

## API 接口文档

### 用户认证

#### POST /api/auth/login

用户登录接口

**请求参数:**
\`\`\`json
{
  "username": "string",
  "password": "string"
}
\`\`\`

**响应示例:**
\`\`\`\`json
{
  "code": 200,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "alice",
      "email": "alice@example.com"
    }
  },
  "msg": "登录成功"
}
\`\`\`\`

### 文档检索

#### POST /api/search/query

智能文档检索接口

**请求参数:**
\`\`\`json
{
  "query": "项目架构设计",
  "knowledge_base_id": 1,
  "limit": 10,
  "model_config": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7
  }
}
\`\`\`

**响应示例:**
\`\`\`json
{
  "code": 200,
  "data": {
    "answer": "根据项目需求和现有技术栈，建议采用微服务架构...",
    "sources": [
      {
        "id": 1,
        "title": "系统架构设计文档",
        "content": "...",
        "score": 0.95
      }
    ]
  },
  "msg": "查询成功"
}
\`\`\`

## 任务清单

- [x] 项目初始化
- [x] 数据库设计
- [x] API 接口开发
- [x] 前端界面开发
- [ ] 单元测试编写
- [ ] 集成测试
- [ ] 部署上线

## 数学公式

行内公式: $E = mc^2$

块级公式:
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$

## 引用和注释

> 这是一个重要的提醒：流式渲染可以显著提升用户体验，让内容逐步展现而不是一次性加载完成。

脚注测试[^1] 和另一个脚注[^2]。

[^1]: 这是第一个脚注的内容
[^2]: 这是第二个脚注的内容，包含更多信息
`
};

// 响应式数据
const selectedExample = ref("basic");
const sseConfig = ref({
  minChunkSize: 1,
  maxChunkSize: 20,
  delay: 20
});
const streamRef = ref(null);
const streamStatus = ref("未开始");
const autoStart = ref(false);

// 计算属性
const currentContent = computed(() => examples[selectedExample.value]);
const isStreaming = computed(() => streamRef.value?.isStreaming || false);

// 方法
const onExampleChange = () => {
  if (!isStreaming.value) {
    resetStream();
  }
};

const startStreaming = () => {
  if (streamRef.value) {
    streamRef.value.startStreaming();
  }
};

const resetStream = () => {
  if (streamRef.value) {
    streamRef.value.reset();
    streamStatus.value = "未开始";
  }
};

const toggleAutoStart = () => {
  autoStart.value = !autoStart.value;
};

// 事件处理
const onStreamStart = () => {
  streamStatus.value = "进行中";
  message.info("开始流式渲染...");
};

const onStreamComplete = () => {
  streamStatus.value = "完成";
  message.success("渲染完成！");
};

const onStreamError = error => {
  streamStatus.value = "错误";
  message.error(`渲染出错: ${error.message}`);
};

// 监听配置变化
watch(
  sseConfig,
  () => {
    if (!isStreaming.value) {
      message.info("SSE 配置已更新");
    }
  },
  { deep: true }
);
</script>

<style scoped lang="scss">
.stream-markdown-example {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;

  h1 {
    text-align: center;
    margin-bottom: 32px;
    color: #262626;
  }
}

.example-controls {
  background: #fafafa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 24px;
  border: 1px solid #f0f0f0;

  .control-group {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;

    &:last-child {
      margin-bottom: 0;
    }

    label {
      font-weight: 500;
      color: #595959;
      min-width: 120px;
    }
  }

  .sse-config {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;

    span {
      color: #8c8c8c;
      font-size: 14px;
    }
  }
}

.example-content {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  min-height: 400px;
}

.example-info {
  margin-top: 24px;

  .action-buttons {
    display: flex;
    gap: 12px;
    justify-content: center;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .stream-markdown-example {
    padding: 16px;
  }

  .example-controls {
    padding: 16px;

    .control-group {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;

      label {
        min-width: auto;
      }
    }

    .sse-config {
      justify-content: center;
    }
  }

  .example-info .action-buttons {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
