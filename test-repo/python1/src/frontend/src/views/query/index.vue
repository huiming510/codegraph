<template>
  <div class="search-container">
    <a-row :gutter="20" class="search-row">
      <!-- 左侧：历史检索记录 -->
      <a-col :xs="24" :lg="6" class="history-col">
        <a-card :bordered="false" class="card-hover history-card">
          <template #title>
            <div class="history-card-title">
              <div style="display: flex; align-items: center; gap: 10px">
                <div class="title-icon breathing">
                  <HistoryOutlined />
                </div>
                <span>历史检索记录</span>
              </div>
              <a-button size="small" @click="clearHistory"> 清空记录 </a-button>
            </div>
          </template>

          <div v-if="searchHistory.length > 0" class="history-list-wrapper">
            <div class="history-list">
              <div
                v-for="record in searchHistory.slice(0, 20)"
                :key="record.id"
                class="history-item"
                @click="loadHistoryRecord(record)"
              >
                <div class="history-content">
                  <div class="history-query">
                    {{ record.query.length > 60 ? record.query.substring(0, 60) + "..." : record.query }}
                  </div>
                  <div class="history-meta">
                    <span class="history-docs">
                      <FileTextOutlined class="meta-icon" />
                      {{ record.sources_count || 0 }} 个文档
                    </span>
                    <span class="history-time">{{ formatTime(record.created_at) }}</span>
                  </div>
                </div>
                <div class="history-actions">
                  <a-button
                    size="small"
                    type="text"
                    danger
                    @click.stop="deleteHistoryRecord(record)"
                    class="delete-btn"
                    :title="'删除这条记录'"
                  >
                    <template #icon>
                      <DeleteOutlined />
                    </template>
                  </a-button>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="history-empty">
            <div class="empty-icon-wrapper">
              <HistoryOutlined class="empty-icon" />
            </div>
            <h4 class="empty-title">暂无历史记录</h4>
            <p class="empty-desc">开始检索后，历史记录将显示在这里</p>
          </div>
        </a-card>
      </a-col>

      <!-- 右侧：业务检索-查看具体知识片段 -->
      <a-col :xs="24" :lg="18" class="result-col">
        <a-card :bordered="false" class="card-hover result-card">
          <template #title>
            <div class="result-card-title">
              <div class="title-icon breathing">
                <SearchOutlined />
              </div>
              <span>业务检索-查看具体知识片段</span>
              <div class="result-actions">
                <a-button type="primary" @click="createNewConversation" class="common-button">
                  <PlusOutlined /> 新建对话
                </a-button>
                <a-button type="primary" @click="showConfigModal = true" class="common-button">
                  <SettingOutlined /> 参数配置
                </a-button>
              </div>
            </div>
          </template>

          <a-space class="result-card-body" direction="vertical" :size="24">
            <!-- 搜索框 -->
            <div class="search-input-wrapper">
              <a-input
                v-model:value="query"
                placeholder="输入您的问题，AI 将从知识库中检索相关内容..."
                size="large"
                @press-enter="handleSearch"
                class="search-input"
              >
                <template #prefix>
                  <SearchOutlined class="search-icon" />
                </template>
              </a-input>
              <a-button type="primary" size="large" @click="handleSearch" :loading="loading" class="common-button">
                <template v-if="!loading">
                  <ThunderboltOutlined />
                  检索
                </template>
              </a-button>
            </div>

            <!-- 结果展示 -->
            <div v-if="streamingResult.sources.length > 0 || streamingResult.answer" class="result-content fade-in">
              <!-- AI 回答 -->
              <div class="ai-answer-wrapper">
                <div class="ai-answer-header">
                  <div class="ai-icon">
                    <RobotOutlined />
                  </div>
                  <span class="ai-title">检索结果</span>
                  <a-tag v-if="!streamingResult.isComplete" color="orange">检索中...</a-tag>
                </div>
                <div class="ai-answer-content">
                  <StreamMarkdown
                    :content="formattedAnswer"
                    :showHeader="false"
                    :autoStart="false"
                    :isStreamComplete="streamingResult.isComplete"
                    ref="streamMarkdownRef"
                  />
                </div>
              </div>

              <!-- 相关文档 -->
              <div v-if="streamingResult.sources.length > 0" class="documents-section">
                <div class="documents-header">
                  <FileSearchOutlined class="documents-icon" />
                  <span class="documents-title">相关文档 ({{ streamingResult.sources.length }}个)</span>
                </div>

                <a-row :gutter="12">
                  <a-col :span="6" v-for="(item, index) in streamingResult.sources" :key="index">
                    <div class="document-card card-hover" @click="downloadDocument(item)">
                      <div class="document-card-header">
                        <FileTextOutlined class="doc-icon" />
                        <div class="document-filename" :title="item.filename">
                          {{ item.filename }}
                        </div>
                      </div>

                      <!-- 文件路径 -->
                      <div class="document-path" :title="item.file_path">
                        路径: {{ item.file_path.length > 30 ? item.file_path.substring(0, 30) + "..." : item.file_path }}
                      </div>

                      <!-- 内容快照 -->
                      <div v-if="item.content_snippet" class="document-snippet">
                        {{ item.content_snippet }}
                      </div>

                      <!-- 相似度 -->
                      <div class="similarity-label">相似度</div>
                      <a-progress
                        :percent="Math.round(item.relevance * 100)"
                        :stroke-color="{ '0%': '#667eea', '100%': '#764ba2' }"
                        size="small"
                      />
                    </div>
                  </a-col>
                </a-row>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-else-if="!loading && !streamingResult.error" class="empty-state">
              <div class="empty-icon-wrapper large">
                <SearchOutlined class="empty-icon large" />
              </div>
              <h3 class="empty-title large">开始检索</h3>
              <p class="empty-desc">输入您的问题，AI 将从知识库中为您找到答案</p>
            </div>

            <!-- 错误状态 -->
            <div v-else-if="streamingResult.error && !loading" class="error-state">
              <div class="error-icon-wrapper">
                <CloseCircleOutlined class="error-icon" />
              </div>
              <h3 class="error-title">查询失败</h3>
              <p class="error-desc">{{ streamingResult.error }}</p>
            </div>
          </a-space>
        </a-card>
      </a-col>
    </a-row>

    <!-- 参数配置弹窗 -->
    <a-modal
      v-model:open="showConfigModal"
      title="检索参数配置"
      width="520px"
      :footer="null"
      :body-style="{ maxHeight: '75vh', overflowY: 'auto', padding: '16px 20px' }"
    >
      <a-form :model="configForm" layout="vertical" :colon="false">
        <!-- 知识库选择 -->
        <a-form-item label="知识库" style="margin-bottom: 10px">
          <a-select v-model:value="configForm.knowledge_base_id" placeholder="选择知识库" allow-clear>
            <a-select-option v-for="kb in knowledgeBases" :key="kb.id" :value="kb.id">
              {{ kb.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <!-- 参数配置：模型、temperature、top_p、检索方式、top_k、threshold -->
        <a-form-item label="模型" style="margin-bottom: 10px">
          <a-select v-model:value="configForm.llm_id" placeholder="选择模型">
            <a-select-option value="Qwen3-30B-A3B-Instruct-2507">Qwen3-30B-A3B-Instruct-2507</a-select-option>
            <a-select-option value="gpt-3.5-turbo">GPT-3.5 Turbo</a-select-option>
            <a-select-option value="gpt-4">GPT-4</a-select-option>
            <a-select-option value="claude-3">Claude 3</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="Temperature" style="margin-bottom: 10px">
          <div style="display: flex; align-items: center; gap: 10px">
            <a-slider v-model:value="configForm.temperature" :min="0" :max="1" :step="0.1" style="flex: 1" />
            <span style="min-width: 35px; text-align: right; font-size: 13px">
              {{ configForm.temperature.toFixed(1) }}
            </span>
          </div>
        </a-form-item>

        <a-form-item label="Top P" style="margin-bottom: 10px">
          <div style="display: flex; align-items: center; gap: 10px">
            <a-slider v-model:value="configForm.top_p" :min="0" :max="1" :step="0.1" style="flex: 1" />
            <span style="min-width: 35px; text-align: right; font-size: 13px">
              {{ configForm.top_p.toFixed(1) }}
            </span>
          </div>
        </a-form-item>

        <a-form-item label="检索方式" style="margin-bottom: 10px">
          <a-select v-model:value="configForm.search_method" placeholder="选择检索方式">
            <a-select-option value="dense">向量检索</a-select-option>
            <a-select-option value="dense_filter">向量+过滤</a-select-option>
            <a-select-option value="hybrid">混合检索</a-select-option>
            <a-select-option value="sparse">稀疏检索</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="Top K" style="margin-bottom: 10px">
          <div style="display: flex; align-items: center; gap: 10px; width: 100%">
            <a-input-number v-model:value="configForm.top_k" :min="1" :max="100" :step="1" style="width: 100%" />
          </div>
        </a-form-item>

        <a-form-item label="相似度阈值 (threshold)" style="margin-bottom: 10px">
          <div style="display: flex; align-items: center; gap: 10px">
            <a-slider v-model:value="configForm.similarity_threshold" :min="0" :max="1" :step="0.1" style="flex: 1" />
            <span style="min-width: 35px; text-align: right; font-size: 13px">
              {{ configForm.similarity_threshold.toFixed(1) }}
            </span>
          </div>
        </a-form-item>

        <!-- 底部按钮 -->
        <a-form-item style="margin-bottom: 0; margin-top: 16px">
          <div style="display: flex; justify-content: flex-end; gap: 10px">
            <a-button @click="handleConfigCancel">取消</a-button>
            <a-button type="primary" @click="handleConfigSave" :loading="savingConfig">保存</a-button>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from "vue";
import { message, Modal } from "ant-design-vue";
import {
  SearchOutlined,
  FileTextOutlined,
  FileSearchOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  CloseCircleOutlined,
  HistoryOutlined,
  DeleteOutlined,
  SettingOutlined,
  PlusOutlined
} from "@ant-design/icons-vue";
import { getQueryHistory, deleteQueryLog, clearQueryLogs, saveQueryResult, queryRAG } from "@/api/modules/queryRag";
import { getKnowledgeBases } from "@/api/modules/knowledgeBase";
import { useUserStore } from "@/stores/modules/user";
import StreamMarkdown from "@/components/StreamMarkdown/index.vue";

const userStore = useUserStore();

// 响应式数据
const query = ref("");
const loading = ref(false);
const streamingResult = ref({
  thinking: "",
  sources: [],
  answer: "",
  isComplete: false,
  queryLogId: null,
  error: null
});
const queryData = ref({});
const knowledgeBases = ref([]);
const searchHistory = ref([]);

// 组件引用
const streamMarkdownRef = ref(null);

// 计算属性：直接透传答案内容
const formattedAnswer = computed(() => streamingResult.value.answer);

// 参数配置相关
const showConfigModal = ref(false);
const savingConfig = ref(false);

/** 默认参数配置（初始值与新建对话时恢复用） */
const DEFAULT_CONFIG = {
  knowledge_base_id: null,
  llm_id: null,
  temperature: 0.1,
  top_p: 0.3,
  search_method: "dense",
  top_k: 20,
  similarity_threshold: 0.2
};

const configForm = ref({ ...DEFAULT_CONFIG });

// ==================== 工具函数 ====================

// 格式化时间显示
const formatTime = timestamp => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffHours < 1) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    return diffMinutes <= 0 ? "刚刚" : `${diffMinutes}分钟前`;
  } else if (diffHours < 24) {
    return `${Math.floor(diffHours)}小时前`;
  } else {
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}天前`;
  }
};

// ==================== 页面导航 ====================

// 新建对话
const createNewConversation = () => {
  // 清空当前搜索状态
  query.value = "";
  streamingResult.value = {
    thinking: "",
    sources: [],
    answer: "",
    isComplete: false,
    queryLogId: null,
    error: null
  };

  // 恢复默认参数配置
  configForm.value = { ...DEFAULT_CONFIG };
  queryData.value.knowledge_base_id = null;

  // 重置 StreamMarkdown 组件
  if (streamMarkdownRef.value) {
    streamMarkdownRef.value.reset();
  }
};

// ==================== 参数配置相关 ====================

// 取消配置
const handleConfigCancel = () => {
  showConfigModal.value = false;
};

// 保存配置
const handleConfigSave = async () => {
  savingConfig.value = true;
  queryData.value.knowledge_base_id = configForm.value.knowledge_base_id;
  queryData.value.model_config = { model: configForm.value.llm_id };

  message.success("配置保存成功");
  showConfigModal.value = false;
  savingConfig.value = false;
};

// ==================== 数据加载 ====================

// 加载查询数据：使用默认配置
const loadQueryData = async () => {
  configForm.value = { ...DEFAULT_CONFIG };
  queryData.value = {
    id: "default",
    title: "智能检索",
    query: "",
    knowledge_base_id: null,
    top_k: 20,
    model_config: { model: configForm.value.llm_id }
  };
};

// 加载知识库
const loadKnowledgeBases = async () => {
  const res = await getKnowledgeBases();
  knowledgeBases.value = res.knowledge_bases || [];
};

// 加载历史记录
const loadSearchHistory = async () => {
  const result = await getQueryHistory();
  searchHistory.value = result.records || [];
};

// 删除单条历史记录
const deleteHistoryRecord = async record => {
  Modal.confirm({
    title: "确认删除这条记录？",
    content: "此操作将永久删除这条历史检索记录，无法恢复。",
    okText: "确认删除",
    cancelText: "取消",
    onOk: async () => {
      await deleteQueryLog(record.id);
      // 重新加载历史记录
      await loadSearchHistory();
      message.success("记录已删除");
    }
  });
};

// 清空历史记录
const clearHistory = () => {
  Modal.confirm({
    title: "确认清空历史记录？",
    content: "此操作将永久删除该检索应用的所有历史记录，无法恢复。",
    okText: "确认清空",
    cancelText: "取消",
    onOk: async () => {
      await clearQueryLogs();
      await loadSearchHistory();
      message.success("历史记录已清空");
    }
  });
};

// 加载历史记录详情
const loadHistoryRecord = record => {
  query.value = record.query;

  // 恢复参数配置（如果历史记录中包含配置信息）
  if (record.model_config || record.knowledge_base_id != null) {
    configForm.value = {
      knowledge_base_id: record.knowledge_base_id,
      llm_id: record.llm_id,
      temperature: record.temperature ?? 0.1,
      top_p: record.top_p ?? 0.3,
      search_method: record.search_method || "dense",
      top_k: record.top_k || 20,
      similarity_threshold: record.similarity_threshold ?? 0.2
    };
  }

  // 先重置 StreamMarkdown 组件
  if (streamMarkdownRef.value) {
    streamMarkdownRef.value.reset();
  }

  // 设置完整的历史记录内容
  streamingResult.value = {
    thinking: "",
    sources: record.sources || [],
    answer: record.answer || "该历史记录暂无完整回答内容",
    isComplete: true,
    queryLogId: record.id,
    error: null
  };

  // 延迟一下，让组件直接渲染完整内容而不是流式渲染
  nextTick(() => {
    if (streamMarkdownRef.value && streamingResult.value.answer) {
      // 直接渲染完整内容，不进行流式渲染
      streamMarkdownRef.value.renderMarkdown(streamingResult.value.answer);
    }
  });
};

// ==================== 主要业务逻辑 ====================

// 执行检索：调用 /query 接口（后端转发到 QA 服务）
const handleSearch = async () => {
  if (!query.value.trim()) {
    message.warning("请输入查询问题");
    return;
  }

  const kbId = configForm.value.knowledge_base_id;
  const llmId = configForm.value.llm_id;
  if (!kbId) {
    message.warning("请先在参数配置中选择知识库");
    return;
  }

  if (!llmId) {
    message.warning("请先在参数配置中选择模型");
    return;
  }

  loading.value = true;
  streamingResult.value = {
    thinking: "",
    sources: [],
    answer: "",
    isComplete: false,
    queryLogId: null,
    error: null
  };

  // 重置 StreamMarkdown 组件
  if (streamMarkdownRef.value) {
    streamMarkdownRef.value.reset();
  }

  try {
    const cfg = configForm.value;

    // 使用流式请求
    await queryRAG(query.value.trim(), {
      knowledgeBaseId: kbId,
      searchAppId: null, // 不使用搜索应用，直接使用知识库
      language: localStorage.getItem("language") || "zh", // 从本地读取语言设置，默认中文
      system_prompt: "请根据提供的信息准确、详细地回答用户的问题。", // 系统提示
      search_options: {
        top_k: parseInt(cfg?.top_k ?? 20), // 确保是整数
        threshold: parseFloat(cfg?.similarity_threshold ?? 0.2), // 确保是小数
        search_method: cfg?.search_method || "dense" // 确保是字符串
      },
      generate_options: {
        model: cfg?.llm_id,
        temperature: parseFloat(cfg?.temperature ?? 0.75),
        top_p: parseFloat(cfg?.top_p ?? 0.95)
      },
      onData: handleStreamData,
      token: userStore.token
    });

    // 只有在没有错误的情况下才保存查询结果和更新历史记录
    if (!streamingResult.value.error) {
      // 流式请求完成后，保存到数据库
      await saveQueryResult({
        query: query.value,
        answer: streamingResult.value.answer,
        sources: streamingResult.value.sources.map(s => ({
          document_id: s.document_id,
          filename: s.filename,
          file_path: s.file_path,
          relevance: s.relevance,
          content_snippet: s.content_snippet
        })),
        knowledge_base_id: kbId,
        search_app_id: Date.now(), // 使用时间戳作为随机ID
        top_k: configForm.value?.top_k || 20,
        // 添加当前参数配置
        llm_id: configForm.value?.llm_id,
        temperature: configForm.value?.temperature,
        top_p: configForm.value?.top_p,
        search_method: configForm.value?.search_method,
        similarity_threshold: configForm.value?.similarity_threshold
      }).catch(err => console.warn("保存查询结果失败:", err));

      await loadSearchHistory();
    }
  } catch (error) {
    streamingResult.value.error = "检索失败";
    message.error("检索失败");
  } finally {
    loading.value = false;
  }
};

// ==================== 事件处理 ====================

// 处理流式数据
const handleStreamData = data => {
  switch (data.type) {
    case "thinking":
      streamingResult.value.thinking = data.content;
      break;
    case "sources":
      // 直接显示相关文档
      streamingResult.value.sources = data.sources || [];
      break;
    case "answer":
      // 直接累积回答内容，处理流式渲染
      if (data.answer) {
        streamingResult.value.answer += data.answer;
      }

      if (data.is_complete) {
        streamingResult.value.isComplete = true;
      }
      break;
    case "complete":
      streamingResult.value.isComplete = true;
      // 查询完成后保存结果到数据库（在 handleSearch 中统一处理）
      break;
    case "error":
      streamingResult.value.error = data.content;
      message.error(data.content);
      break;
  }
};

// 下载文档文件
const downloadDocument = doc => {
  // 检查是否有文件路径
  if (!doc.file_path || doc.file_path.trim() === "") {
    message.warning("该文档没有可用的下载路径");
    return;
  }

  try {
    // 检查是否在浏览器环境中
    if (typeof window === "undefined" || !window.document) {
      message.error("当前环境不支持文件下载");
      return;
    }

    // 使用 window.open 作为备用方案
    const link = window.document.createElement("a");
    link.href = doc.file_path;
    link.download = doc.filename || "document";
    link.target = "_blank";

    // 添加到DOM并触发点击
    window.document.body.appendChild(link);
    link.click();

    // 清理
    window.document.body.removeChild(link);

    // message.success(`开始下载: ${doc.filename}`);
  } catch (error) {
    message.error("下载文档失败，请尝试右键保存链接");
  }
};

// ==================== 生命周期 ====================

onMounted(async () => {
  await loadKnowledgeBases();
  await loadQueryData();
  loadSearchHistory();
});
</script>

<style scoped lang="scss">
/* 容器样式 */
.search-container {
  padding: 15px;
  height: 100%;
}

.search-row {
  height: 100%;
  overflow: hidden;
}

.history-col,
.result-col {
  height: 100%;
}

/* 卡片标题样式 */
.history-card-title,
.result-card-title {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.title-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 8px;

  .anticon {
    font-size: 16px;
    color: white;
  }
}

/* 右侧操作按钮样式 */
.result-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

/* 历史记录样式 */
.history-list-wrapper {
  height: 100%;
  overflow: hidden;
  overflow-y: auto;
}

.history-list {
  padding: 4px 0;
}

.history-item {
  margin-bottom: 8px;
  padding: 12px 16px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;

  &:hover {
    background: #f5f5f5;
    border-color: #667eea;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
  }

  &:last-child {
    margin-bottom: 0;
  }
}

.history-content {
  flex: 1;
  cursor: pointer;
}

.history-actions {
  opacity: 0;
  transition: opacity 0.2s ease;
  margin-left: 8px;
}

.history-item:hover .history-actions {
  opacity: 1;
}

.history-query {
  font-size: 14px;
  font-weight: 500;
  color: #262626;
  line-height: 1.4;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;

  .history-docs {
    display: flex;
    align-items: center;
    color: #666;
    font-weight: 500;
  }

  .history-time {
    color: #8c8c8c;
    font-weight: 500;
  }
}

.meta-icon {
  font-size: 12px;
  margin-right: 4px;
}

.delete-btn {
  opacity: 0.7;
}

/* 空状态样式 */
.history-empty {
  padding: 80px 20px;
  text-align: center;
  height: calc(100% - 80px);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, rgb(102 126 234 / 10%), rgb(118 75 162 / 10%));
  border-radius: 50%;

  &.large {
    width: 80px;
    height: 80px;
    margin-bottom: 20px;
  }
}

.empty-icon {
  font-size: 24px;
  color: #667eea;

  &.large {
    font-size: 32px;
  }
}

.empty-title {
  margin: 0 0 8px;
  color: #262626;

  &.large {
    margin: 0 0 8px;
  }
}

.empty-desc {
  margin: 0;
  color: #8c8c8c;
  font-size: 13px;
}

/* 搜索区域样式 */
.search-input-wrapper {
  display: flex;
  gap: 12px;
  padding: 0 24px;
}

.search-input {
  flex: 1;
}

.search-icon {
  color: #667eea;
}

.common-button {
  min-width: 100px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
}

/* 结果区域样式 */
.result-content {
  padding: 0;
}

.ai-answer-wrapper {
  padding: 20px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, rgb(102 126 234 / 5%), rgb(118 75 162 / 5%));
  border-radius: 12px;
}

.ai-answer-header {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.ai-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 8px;

  .anticon {
    font-size: 18px;
    color: white;
  }
}

.ai-title {
  font-weight: 600;
  color: #667eea;
}

.ai-answer-content {
  margin: 0;
}

/* 文档区域样式 */
.documents-section {
  margin-top: 20px;
}

.documents-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.documents-icon {
  color: #667eea;
}

.documents-title {
  font-weight: 500;
}

.document-card {
  padding: 16px;
  margin-bottom: 12px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  cursor: pointer;
}

.document-card-header {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.doc-icon {
  font-size: 20px;
  color: #667eea;
}

.document-filename {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
  white-space: nowrap;
}

.document-path {
  margin-bottom: 8px;
  font-size: 12px;
  color: #8c8c8c;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-snippet {
  margin-bottom: 8px;
  font-size: 13px;
  color: #666;
  line-height: 1.4;
  height: 2.8em; /* 两行高度，1.4 * 2 = 2.8em */
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  text-overflow: ellipsis;
}

.similarity-label {
  margin-bottom: 8px;
  font-size: 12px;
  color: #8c8c8c;
}

/* 错误状态样式 */
.error-state {
  padding: 40px 0;
  text-align: center;
}

.error-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, rgb(255 77 79 / 10%), rgb(255 77 79 / 10%));
  border-radius: 50%;
}

.error-icon {
  font-size: 32px;
  color: #ff4d4f;
}

.error-title {
  margin: 0 0 8px;
  color: #262626;
}

.error-desc {
  margin: 0;
  color: #8c8c8c;
}

/* 卡片样式优化 */
.result-card {
  height: 100%;
  :deep(.ant-card-body) {
    padding: 24px 0 0;
    height: calc(100% - 52px);
  }

  :deep(.result-card-body) {
    width: 100%;
    height: 100%;

    .ant-space-item:last-child {
      padding: 0 24px;
      margin-bottom: 5px;
      height: calc(100% - 64px);
      overflow: hidden;
      overflow-y: auto;
      .empty-state {
        text-align: center;
      }
    }
  }
}

.history-card {
  height: 100%;
  :deep(.ant-card-body) {
    padding-right: 0;
    height: calc(100% - 80px);
    margin-right: 24px;
    overflow: hidden;
    overflow-y: auto;
  }
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  animation: fadeIn 0.3s ease;
}

/* 滚动条样式 */
.history-list::-webkit-scrollbar {
  width: 4px;
}

.history-list::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 2px;
}

.history-list::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 2px;

  &:hover {
    background: #ccc;
  }
}

/* 响应式调整 */
@media (max-width: 992px) {
  .history-item {
    padding: 10px 12px;
    margin-bottom: 6px;
  }

  .search-input-wrapper {
    flex-direction: column;
  }

  .common-button {
    width: 100%;
  }
}
</style>
