<template>
  <div class="chat-container">
    <!-- 会话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <span class="sidebar-title">会话列表</span>
        <a-button
          type="primary"
          size="small"
          @click="handleNewSession"
          style="background: linear-gradient(135deg, #667eea, #764ba2); border: none"
        >
          <PlusOutlined />
          新建
        </a-button>
      </div>
      <div class="sessions-list">
        <Conversations :items="sessionList" :active-key="curSession" @active-change="handleSessionChange" />
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="chat-main">
      <!-- Header -->
      <div class="chat-header">
        <div class="chat-title">
          <div class="chat-icon">
            <CommentOutlined />
          </div>
          <div>
            <span style="font-size: 18px; font-weight: 600">{{ currentApp?.name || 'AI 助手' }}</span>
            <span style="font-size: 13px; color: #8c8c8c; margin-left: 8px">对话</span>
          </div>
          <div class="online-tag">
            <span class="online-dot"></span>
            在线
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: center">
          <a-button type="text" size="small" @click="openConfigModal" title="对话配置">
            <SettingOutlined />
          </a-button>
          <a-select v-model:value="selectedKbId" placeholder="选择知识库" style="width: 180px" :loading="loadingKbs" size="small">
            <a-select-option
              v-for="kb in (currentApp?.kb_ids?.length ? knowledgeBases.filter(k => currentApp.kb_ids.includes(k.id)) : knowledgeBases)"
              :key="kb.id"
              :value="kb.id"
            >
              <span style="margin-right: 6px">{{ kb.icon }}</span>
              {{ kb.name }}
            </a-select-option>
          </a-select>
          <a-dropdown>
            <a-button type="text">
              <DeleteOutlined />
              更多
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="handleClearSession" :disabled="!messages.length">
                  清空当前消息
                </a-menu-item>
                <a-menu-item danger @click="handleDeleteConversation" :disabled="!curSession">
                  删除当前对话
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>

      <!-- 对话配置弹窗 -->
      <a-modal
        v-model:open="showConfigModal"
        title="对话配置"
        width="520px"
        destroy-on-close
        ok-text="保存"
        cancel-text="取消"
        :confirm-loading="configSaving"
        @ok="handleConfigSave"
        @cancel="handleConfigCancel"
      >
        <a-form layout="vertical" :label-col="{ span: 12 }" :colon="false">
          <a-form-item label="角色" style="margin-bottom: 12px">
            <a-textarea
              v-model:value="chatConfig.description"
              placeholder="你是一位智能助手。"
              :rows="2"
              :maxlength="200"
              size="small"
            />
          </a-form-item>
          <a-divider orientation="center">检索配置 (search_options)</a-divider>
          <a-form-item label="top_k（召回数量）" style="margin-bottom: 12px">
            <a-input-number v-model:value="chatConfig.search_options.top_k" :min="1" :max="100" style="width: 100%" size="small" />
          </a-form-item>
          <a-form-item label="threshold（相似度阈值）" style="margin-bottom: 12px">
            <a-input-number v-model:value="chatConfig.search_options.threshold" :min="0" :max="1" :step="0.01" style="width: 100%" size="small" />
          </a-form-item>
          <a-form-item label="search_method（检索方式）" style="margin-bottom: 12px">
            <a-select v-model:value="chatConfig.search_options.search_method" style="width: 100%" size="small">
              <a-select-option v-for="opt in searchMethodOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-divider orientation="center">生成配置 (generate_options)</a-divider>
          <a-form-item label="temperature（温度）" style="margin-bottom: 12px">
            <a-input-number v-model:value="chatConfig.generate_options.temperature" :min="0" :max="2" :step="0.05" style="width: 100%" size="small" />
          </a-form-item>
          <a-form-item label="top_p" style="margin-bottom: 12px">
            <a-input-number v-model:value="chatConfig.generate_options.top_p" :min="0" :max="1" :step="0.01" style="width: 100%" size="small" />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- 消息列表 -->
      <div ref="messagesContainer" class="chat-list">
        <!-- 欢迎界面 -->
        <template v-if="!messages.length">
          <Welcome
            variant="borderless"
            title="👋 您好，我是 AI 助手"
            description="基于知识库为您提供智能问答服务，请输入您的问题"
            class="chat-welcome"
          >
            <template #icon>
              <div class="welcome-icon">
                <CommentOutlined />
              </div>
            </template>
          </Welcome>
          <Prompts
            vertical
            title="试试这些问题："
            :items="promptItems"
            @item-click="handlePromptClick"
            style="margin-inline: 16px"
          />
        </template>

        <!-- 消息气泡 -->
        <template v-else>
          <div class="messages-wrapper">
            <div v-for="(msg, index) in messages" :key="index" class="message-item">
              <Bubble
                :content="msg.content"
                :placement="msg.role === 'user' ? 'end' : 'start'"
                :typing="false"
                :avatar="msg.role === 'user' ? { style: userAvatarStyle } : { style: aiAvatarStyle }"
              >
                <template #avatar>
                  <div :class="['bubble-avatar', msg.role]">
                    {{ msg.role === "assistant" ? "AI" : "U" }}
                  </div>
                </template>
              </Bubble>
              <!-- 参照文档卡片：仅 assistant 消息且有 references 时显示 -->
              <div v-if="msg.role === 'assistant' && msg.references?.length" class="ref-cards">
                <a-tooltip
                  v-for="(ref, refIdx) in msg.references"
                  :key="ref.ref_id ?? ref.chunk_id ?? refIdx"
                  placement="top"
                >
                  <template #title>
                    <span style="white-space: pre-line">{{ getRefTooltip(ref) }}</span>
                  </template>
                  <div class="ref-card">
                    <span class="ref-badge">[{{ ref.ref_id ?? refIdx + 1 }}]</span>
                    <span class="ref-name">{{ getRefDisplayName(ref) }}</span>
                  </div>
                </a-tooltip>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 输入框 -->
      <div class="chat-send">
        <div class="thinking-mode-bar">
          <button
            type="button"
            :class="['thinking-mode-btn', { active: isThinkingMode }]"
            title="思考模式"
            @click="isThinkingMode = !isThinkingMode"
          >
            <BulbOutlined />
            <span>思考模式</span>
          </button>
        </div>
        <Sender
          :loading="loading"
          :value="inputValue"
          placeholder="输入您的问题，按 Enter 发送..."
          @change="handleInputChange"
          @submit="handleSubmit"
          @cancel="handleCancel"
        />
        <div class="send-hint">
          <span>按 Enter 发送，Shift + Enter 换行</span>
          <span>AI 回答基于知识库内容</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { message, Modal } from "ant-design-vue";
import { PlusOutlined, DeleteOutlined, CommentOutlined, SettingOutlined, BulbOutlined } from "@ant-design/icons-vue";
import { Bubble, Conversations, Prompts, Sender, Welcome } from "ant-design-x-vue";
import { sendChatStream, getChatHistory, updateSessionTitle } from "@/api/modules/chat";
import { getKnowledgeBases } from "@/api/modules/knowledgeBase";
import { getChatAppDetail, getAppConversations, createAppConversation, updateChatAppConfig, deleteChatSession } from "@/api/modules/chatApp";
import { defaultSearchOptions, defaultGenerateOptions, searchMethodOptions } from "@/constants/chatConfig";

const route = useRoute();
const router = useRouter();

/** 当前助手 session_key（app_ 开头），从路由 query 获取，支持 app_session_key 或 session_key */
const appSessionKey = computed(() => route.query?.app_session_key || route.query?.session_key || "");

// State
const inputValue = ref("");
const loading = ref(false);
const messagesContainer = ref(null);
const messages = ref([]);
const curSession = ref("");
const sessionList = ref([]);
/** 创建新对话后设置 curSession 时，跳过 watcher 对 messages 的覆盖，避免竞态导致首条消息被清空 */
const skipNextSessionLoad = ref(false);
const messageHistory = ref({});
/** 当前助手详情（含 search_options、generate_options、kb_ids），配置继承给该助手下所有对话 */
const currentApp = ref(null);

// 知识库相关
const knowledgeBases = ref([]);
const selectedKbId = ref(null);
const loadingKbs = ref(false);
const showKbSelector = ref(false);

/** 思考模式：默认暗色，点击高亮 */
const isThinkingMode = ref(false);

// 对话配置弹窗
const showConfigModal = ref(false);
const configSaving = ref(false);
/** 打开弹窗时的配置快照，用于取消时还原 */
const configSnapshot = ref(null);

/** 对话配置：description、search_options、generate_options，对应流式对话 API 与助手配置 */
const chatConfig = ref({
  description: "你是一位智能助手。",
  search_options: { ...defaultSearchOptions },
  generate_options: { ...defaultGenerateOptions }
});

// 问题提示
const promptItems = [
  { key: "1", description: "什么是 Python？" },
  { key: "2", description: "介绍一下机器学习" },
  { key: "3", description: "FastAPI 有什么特点？" },
  { key: "4", description: "Vue3 的新特性有哪些？" }
];

// 气泡角色配置
const userAvatarStyle = {
  background: "linear-gradient(135deg, #667eea, #764ba2)",
  color: "#fff"
};

const aiAvatarStyle = {
  background: "linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2))",
  color: "#667eea"
};

// 加载知识库列表
const loadKnowledgeBases = async () => {
  loadingKbs.value = true;
  try {
    const res = await getKnowledgeBases();
    knowledgeBases.value = res.knowledge_bases || [];
    // 默认选择第一个
    if (knowledgeBases.value.length > 0 && !selectedKbId.value) {
      selectedKbId.value = knowledgeBases.value[0].id;
    }
  } catch (e) {
    message.error("加载知识库失败");
  } finally {
    loadingKbs.value = false;
  }
};

/** 从后端加载会话历史，保留 role、content、references 以维持原样式（气泡 + 参照文档卡片） */
const loadHistoryForSession = async sessionKey => {
  try {
    const res = await getChatHistory(sessionKey);
    const list = res?.messages || [];
    return list.map(m => ({
      role: m.role,
      content: m.content,
      references: m.references || []
    }));
  } catch {
    return [];
  }
};

// 当助手变化时：加载助手详情、对话列表，并恢复 chatConfig、selectedKbId
watch(
  appSessionKey,
  async (key) => {
    if (!key) {
      currentApp.value = null;
      sessionList.value = [];
      curSession.value = "";
      return;
    }
    try {
      const app = await getChatAppDetail(key);
      currentApp.value = app;
      chatConfig.value.description = app.description || "你是一位智能助手。";
      chatConfig.value.search_options = { ...defaultSearchOptions, ...(app.search_options || {}) };
      chatConfig.value.generate_options = { ...defaultGenerateOptions, ...(app.generate_options || {}) };
      if (app.kb_ids?.length && knowledgeBases.value.some(k => k.id === app.kb_ids[0])) {
        selectedKbId.value = app.kb_ids[0];
      }
      const convRes = await getAppConversations(key);
      let convs = convRes.conversations || [];
      const fromConv = route.query?.conv_session_key;
      if (convs.length === 0) {
        try {
          const res = await createAppConversation(key);
          convs = [{ session_key: res.session_key, title: "新对话" }];
          skipNextSessionLoad.value = true;
          curSession.value = res.session_key;
        } catch {
          convs = [];
          curSession.value = "";
        }
      } else if (fromConv && convs.some(c => c.session_key === fromConv)) {
        curSession.value = fromConv;
      } else {
        curSession.value = convs[0].session_key;
      }
      sessionList.value = convs.map(c => ({ key: c.session_key, label: c.title || "新对话", group: "今天" }));
    } catch {
      currentApp.value = null;
      sessionList.value = [];
      curSession.value = "";
    }
  },
  { immediate: true }
);

// 切换对话：优先用本地缓存，否则从后端拉取；配置始终来自 currentApp（助手）
watch(
  curSession,
  async (key) => {
    if (!key) return;
    if (skipNextSessionLoad.value) {
      skipNextSessionLoad.value = false;
      return;
    }
    const cached = messageHistory.value[key];
    if (cached?.length) {
      messages.value = [...cached];
      return;
    }
    const history = await loadHistoryForSession(key);
    messages.value = history;
    if (history.length) {
      messageHistory.value[key] = history;
    }
  },
  { immediate: true }
);

// 保存消息历史
watch(
  messages,
  () => {
    if (messages.value.length) {
      messageHistory.value[curSession.value] = [...messages.value];
    }
  },
  { deep: true }
);

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

// 流式回答时标记 isTyping，便于显示光标等状态；内容随 delta 实时渲染
const startTyping = msgIndex => {
  const msg = messages.value[msgIndex];
  if (!msg) return;
  msg.isTyping = true;
  scrollToBottom();
};

const stopTyping = msgIndex => {
  const msg = messages.value[msgIndex];
  if (!msg) return;
  msg.isTyping = false;
};

// 事件处理
const handleInputChange = val => {
  inputValue.value = val;
};

/** 参照文档卡片展示名：文件名 + 工作表名（若有） */
const getRefDisplayName = ref => {
  const meta = ref?.metadata || {};
  const name = meta.file_name || "未知文档";
  const sheet = meta.sheet_name;
  return sheet ? `${name} · ${sheet}` : name;
};

/** 悬浮提示：完整元信息 */
const getRefTooltip = ref => {
  const meta = ref?.metadata || {};
  const parts = [];
  if (meta.file_name) parts.push(`文件：${meta.file_name}`);
  if (meta.sheet_name) parts.push(`工作表：${meta.sheet_name}`);
  if (ref?.chunk_id) parts.push(`块 ID：${ref.chunk_id}`);
  if (ref?.doc_id) parts.push(`文档 ID：${ref.doc_id}`);
  return parts.length ? parts.join("\n") : "参照文档";
};

// 根据知识库解析 ES 索引名
const resolveKbIndex = kbId => {
  const kb = knowledgeBases.value.find(k => k.id === kbId);
  if (!kb) return `linkrag_kb_${kbId}`;
  return (kb.es_id && kb.es_id.trim()) || `linkrag_kb_${kb.id}`;
};

const handleSubmit = async () => {
  const text = inputValue.value.trim();
  if (!text || loading.value) return;

  if (!appSessionKey.value) {
    message.warning("请先选择助手");
    return;
  }
  if (!selectedKbId.value) {
    message.warning("请选择知识库");
    return;
  }

  // 无当前对话时自动创建
  if (!curSession.value) {
    try {
      const res = await createAppConversation(appSessionKey.value);
      await loadConversations();
      skipNextSessionLoad.value = true;
      curSession.value = res.session_key;
    } catch (e) {
      message.error("创建对话失败");
      return;
    }
  }

  inputValue.value = "";

  // 添加用户消息
  messages.value.push({
    role: "user",
    content: text
  });

  // 更新会话标题（首条消息时持久化到后端）
  const session = sessionList.value.find(s => s.key === curSession.value);
  if (session?.label === "新对话") {
    const newTitle = text.slice(0, 20) + (text.length > 20 ? "..." : "");
    session.label = newTitle;
    updateSessionTitle(curSession.value, newTitle).catch(() => {});
  }

  scrollToBottom();
  loading.value = true;

  const msgIndex = messages.value.length;
  messages.value.push({
    role: "assistant",
    content: "",
    references: [],
    isTyping: true
  });
  scrollToBottom();

  try {
    await sendChatStream(
      {
        sessionId: curSession.value,
        utterance: text,
        index: resolveKbIndex(selectedKbId.value),
        appSessionKey: appSessionKey.value,
        systemPrompt: chatConfig.value.description || undefined,
        searchOptions: { ...chatConfig.value.search_options },
        generateOptions: { ...chatConfig.value.generate_options }
      },
      {
        onChunk: chunk => {
          const msg = messages.value[msgIndex];
          if (msg) msg.content = msg.content + chunk;
          scrollToBottom();
        },
        onReferences: refs => {
          const msg = messages.value[msgIndex];
          if (msg) msg.references = refs;
          scrollToBottom();
        },
        onDone: () => {
          stopTyping(msgIndex);
          const msg = messages.value[msgIndex];
          if (msg && !msg.content) msg.content = "（暂无回复）";
          loading.value = false;
        }
      }
    );
  } catch (error) {
    const msg = messages.value[msgIndex];
    if (msg) msg.content = `（发送失败：${error?.message || "请重试"}）`;
    stopTyping(msgIndex);
    message.error(error?.message || "发送失败，请重试");
  } finally {
    loading.value = false;
  }
};

const handleCancel = () => {
  loading.value = false;
};

const handlePromptClick = info => {
  inputValue.value = info.data.description;
  handleSubmit();
};

const handleNewSession = async () => {
  if (loading.value) {
    message.warning("请等待当前对话完成");
    return;
  }
  if (!appSessionKey.value) {
    message.warning("请先选择助手");
    return;
  }
  try {
    const res = await createAppConversation(appSessionKey.value);
    await loadConversations();
    curSession.value = res.session_key;
    messages.value = [];
    message.success("已创建新对话");
  } catch (e) {
    message.error("创建对话失败");
  }
};

const handleSessionChange = key => {
  curSession.value = key;
};

const handleClearSession = () => {
  messages.value = [];
  messageHistory.value[curSession.value] = [];
  message.success("已清空当前消息");
};

/** 删除当前对话（从后端删除并刷新列表） */
const handleDeleteConversation = () => {
  if (!curSession.value) return;
  Modal.confirm({
    title: "确认删除",
    icon: () => null,
    content: "确定要删除当前对话吗？删除后无法恢复。",
    okText: "删除",
    okType: "danger",
    async onOk() {
      try {
        await deleteChatSession(curSession.value);
        delete messageHistory.value[curSession.value];
        await loadConversations();
        const list = sessionList.value;
        if (list.length > 0) {
          curSession.value = list[0].key;
        } else {
          curSession.value = "";
          messages.value = [];
        }
        message.success("已删除");
      } catch (e) {
        message.error("删除失败");
      }
    }
  });
};

/** 打开对话配置弹窗前，从数据库拉取最新配置，保证展示的是最新数据 */
const openConfigModal = async () => {
  const key = appSessionKey.value;
  if (!key || !key.startsWith("app_")) return;
  try {
    const app = await getChatAppDetail(key);
    currentApp.value = app;
    chatConfig.value.description = app.description || "你是一位智能助手。";
    chatConfig.value.search_options = { ...defaultSearchOptions, ...(app.search_options || {}) };
    chatConfig.value.generate_options = { ...defaultGenerateOptions, ...(app.generate_options || {}) };
    configSnapshot.value = JSON.parse(JSON.stringify(chatConfig.value));
    showConfigModal.value = true;
  } catch (e) {
    message.error("加载配置失败");
  }
};

/** 打开配置弹窗时保存快照（openConfigModal 已提前拉取并保存，此处保留兼容） */
watch(showConfigModal, val => {
  if (val && !configSnapshot.value) configSnapshot.value = JSON.parse(JSON.stringify(chatConfig.value));
});

/** 保存配置：持久化到助手（app_），该助手下所有对话继承此配置 */
const handleConfigSave = async () => {
  const key = appSessionKey.value;
  if (!key || !key.startsWith("app_")) {
    message.info("请先选择助手");
    return;
  }
  configSaving.value = true;
  try {
    await updateChatAppConfig(key, {
      description: chatConfig.value.description,
      search_options: { ...chatConfig.value.search_options },
      generate_options: { ...chatConfig.value.generate_options }
    });
    if (currentApp.value) {
      currentApp.value.description = chatConfig.value.description;
      currentApp.value.search_options = { ...chatConfig.value.search_options };
      currentApp.value.generate_options = { ...chatConfig.value.generate_options };
    }
    message.success("配置已保存");
    showConfigModal.value = false;
  } catch (e) {
    message.error("保存失败");
    throw e;
  } finally {
    configSaving.value = false;
  }
};

/** 取消配置：还原为打开时的值 */
const handleConfigCancel = () => {
  if (configSnapshot.value) {
    chatConfig.value = JSON.parse(JSON.stringify(configSnapshot.value));
  }
};

/** 加载当前助手下对话列表 */
const loadConversations = async () => {
  const key = appSessionKey.value;
  if (!key) return;
  try {
    const res = await getAppConversations(key);
    const convs = res?.conversations || [];
    sessionList.value = convs.map(c => ({ key: c.session_key, label: c.title || "新对话", group: "今天" }));
    if (convs.length > 0 && !curSession.value) {
      curSession.value = convs[0].session_key;
    }
  } catch {
    sessionList.value = [];
  }
};

onMounted(async () => {
  loadKnowledgeBases();
  if (!appSessionKey.value) {
    router.replace({ path: "/chat/list" });
    return;
  }
});
</script>

<style scoped>
.chat-container {
  display: flex;
  gap: 20px;
  height: calc(100vh - 130px);
  padding: 15px;
}

.chat-sidebar {
  display: flex;
  flex-direction: column;
  width: 280px;
  overflow: hidden;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgb(0 0 0 / 6%);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 600;
}

.sessions-list {
  flex: 1;
  padding: 12px;
  overflow: auto;
}

.chat-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgb(0 0 0 / 6%);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.chat-title {
  display: flex;
  gap: 12px;
  align-items: center;
}

.chat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 18px;
  color: #ffffff;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 10px;
}

.online-tag {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  padding: 4px 12px;
  font-size: 12px;
  color: #52c41a;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 12px;
}

.online-dot {
  width: 6px;
  height: 6px;
  background: #52c41a;
  border-radius: 50%;
}

.chat-list {
  flex: 1;
  padding: 20px;
  overflow: auto;
  background: linear-gradient(180deg, #fafafa 0%, #f5f5f5 100%);
}

.chat-welcome {
  padding: 16px 20px;
  margin-inline: 16px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, rgb(102 126 234 / 10%), rgb(118 75 162 / 10%));
  border-radius: 4px 16px 16px;
}

.welcome-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  font-size: 28px;
  color: #ffffff;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 16px;
}

.chat-send {
  padding: 16px 20px;
  background: #ffffff;
  border-top: 1px solid #f0f0f0;
}

.thinking-mode-bar {
  margin-bottom: 12px;
}

.thinking-mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  color: #8c8c8c;
  background: #f5f5f5;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: color 0.2s, background 0.2s, border-color 0.2s;
}

.thinking-mode-btn:hover {
  color: #595959;
  background: #efefef;
  border-color: #d9d9d9;
}

.thinking-mode-btn.active {
  color: #fff;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-color: transparent;
}

.thinking-mode-btn.active:hover {
  filter: brightness(1.05);
}

.send-hint {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: #8c8c8c;
}

/* 消息列表样式 */
.messages-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bubble-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 50%;
}

.bubble-avatar.assistant {
  color: #667eea;
  background: linear-gradient(135deg, rgb(102 126 234 / 20%), rgb(118 75 162 / 20%));
}

.bubble-avatar.user {
  color: #ffffff;
  background: linear-gradient(135deg, #667eea, #764ba2);
}

/* 消息项：气泡 + 参照文档 */
.message-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 参照文档卡片：仅 assistant 消息时左对齐 */
.ref-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: 52px;
  max-width: 85%;
}

.ref-card {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  color: #667eea;
  background: linear-gradient(135deg, rgb(102 126 234 / 8%), rgb(118 75 162 / 8%));
  border: 1px solid rgb(102 126 234 / 25%);
  border-radius: 8px;
  cursor: default;
  transition: background 0.2s, border-color 0.2s;
}

.ref-card:hover {
  background: linear-gradient(135deg, rgb(102 126 234 / 14%), rgb(118 75 162 / 14%));
  border-color: rgb(102 126 234 / 45%);
}

.ref-badge {
  font-weight: 600;
  color: #764ba2;
}

.ref-name {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
