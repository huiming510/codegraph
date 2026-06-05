<template>
  <div class="chat-container">
    <!-- 页面标题 -->
    <div class="page-title">学习业务知识，解决你的疑惑</div>
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <a-tag color="purple">{{ sessions.length }} 个助手</a-tag>
      </div>
      <a-button
        type="primary"
        @click="showCreateModal = true"
        style="background: linear-gradient(135deg, #667eea, #764ba2); border: none"
      >
        <PlusOutlined /> 新建助手
      </a-button>
    </div>

    <!-- 会话卡片列表 -->
    <a-spin :spinning="loading">
      <div v-if="sessions.length === 0" class="empty-state">
        <CommentOutlined style="font-size: 64px; color: #d9d9d9" />
        <h3>暂无助手</h3>
        <p>创建您的第一个助手，配置知识库与对话参数后开始智能问答</p>
        <a-button type="primary" @click="showCreateModal = true"> <PlusOutlined /> 新建助手 </a-button>
      </div>

      <a-row v-else :gutter="20">
        <a-col :span="6" v-for="session in sessions" :key="session.id">
          <a-card :bordered="false" class="session-card card-hover">
            <div class="session-click-area" @click="goToChat(session)">
              <div class="session-icon">
                <MessageOutlined />
              </div>
              <div class="session-info">
                <h3 class="session-title">{{ session.name || "新对话" }}</h3>
                <p class="session-summary">{{ truncate(session.description, 50) }}</p>
                <div class="session-meta">
                  <a-tag v-if="session.kb_ids && session.kb_ids.length" color="blue">
                    {{ session.kb_ids.length }} 个知识库
                  </a-tag>
                  <a-tag v-if="session.conversation_count !== undefined" color="cyan">
                    {{ session.conversation_count }} 个对话
                  </a-tag>
                  <span class="session-time">{{ formatDate(session.updated_at || session.created_at) }}</span>
                </div>
              </div>
            </div>
            <div class="session-actions" @click.stop>
              <a-dropdown>
                <a-button type="text" size="small">
                  <MoreOutlined />
                </a-button>
                <template #overlay>
                  <a-menu>
                    <a-menu-item @click="editSession(session)"> <EditOutlined /> 编辑 </a-menu-item>
                    <a-menu-item danger @click="confirmDelete(session)"> <DeleteOutlined /> 删除 </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- 新建/编辑助手弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      :title="editingSession ? '编辑助手' : '助手设置'"
      width="520px"
      :body-style="{ maxHeight: '75vh', overflowY: 'auto', padding: '16px 20px' }"
    >
      <a-form :model="sessionForm" layout="vertical" :colon="false">
        <!-- 名称 -->
        <a-form-item required style="margin-bottom: 12px">
          <template #label> 助手名称 </template>
          <a-input v-model:value="sessionForm.name" placeholder="请输入助手名称" size="small" />
        </a-form-item>

        <!-- 头像上传 -->
        <a-form-item label="助手头像" style="margin-bottom: 12px">
          <a-upload
            v-model:file-list="fileList"
            list-type="picture-card"
            :before-upload="beforeUpload"
            :max-count="1"
            accept="image/*"
            @change="handleAvatarChange"
          >
            <div v-if="fileList.length === 0" style="font-size: 12px">
              <PlusOutlined style="font-size: 16px" />
              <div style="margin-top: 2px">上传</div>
            </div>
          </a-upload>
        </a-form-item>

        <!-- 角色 -->
        <a-form-item label="角色" style="margin-bottom: 12px">
          <a-textarea v-model:value="sessionForm.description" placeholder="你是一位智能助手。" :rows="2" :maxlength="200" />
        </a-form-item>

        <!-- 知识库 - 多选 -->
        <a-form-item style="margin-bottom: 12px">
          <template #label> 知识库 </template>
          <a-select
            v-model:value="sessionForm.kb_ids"
            mode="multiple"
            placeholder="请选择知识库"
            :loading="loadingKbs"
            size="small"
            :max-tag-count="2"
          >
            <a-select-option v-for="kb in knowledgeBases" :key="kb.id" :value="kb.id">
              {{ kb.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <!-- 检索配置 (search_options) - 与 detail 保持一致 -->
        <a-divider orientation="center">检索配置 (search_options)</a-divider>
        <a-form-item label="top_k（召回数量）" style="margin-bottom: 12px">
          <a-input-number v-model:value="sessionForm.search_options.top_k" :min="1" :max="100" style="width: 100%" size="small" />
        </a-form-item>
        <a-form-item label="threshold（相似度阈值）" style="margin-bottom: 12px">
          <a-input-number
            v-model:value="sessionForm.search_options.threshold"
            :min="0"
            :max="1"
            :step="0.01"
            style="width: 100%"
            size="small"
          />
        </a-form-item>
        <a-form-item label="search_method（检索方式）" style="margin-bottom: 12px">
          <a-select v-model:value="sessionForm.search_options.search_method" style="width: 100%" size="small">
            <a-select-option v-for="opt in searchMethodOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <!-- 生成配置 (generate_options) - 与 detail 保持一致 -->
        <a-divider orientation="center">生成配置 (generate_options)</a-divider>
        <a-form-item label="temperature（温度）" style="margin-bottom: 12px">
          <a-input-number
            v-model:value="sessionForm.generate_options.temperature"
            :min="0"
            :max="2"
            :step="0.05"
            style="width: 100%"
            size="small"
          />
        </a-form-item>
        <a-form-item label="top_p" style="margin-bottom: 12px">
          <a-input-number
            v-model:value="sessionForm.generate_options.top_p"
            :min="0"
            :max="1"
            :step="0.01"
            style="width: 100%"
            size="small"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 10px">
          <a-button size="small" @click="handleCancel">取消</a-button>
          <a-button size="small" type="primary" @click="handleSaveSession" :loading="saving">保存</a-button>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { message, Modal } from "ant-design-vue";
import {
  CommentOutlined,
  MessageOutlined,
  PlusOutlined,
  MoreOutlined,
  EditOutlined,
  DeleteOutlined
} from "@ant-design/icons-vue";
import { getKnowledgeBases } from "@/api/modules/knowledgeBase";
import { getChatApps, createChatApp, updateChatApp, deleteChatApp, getChatAppDetail } from "@/api/modules/chatApp";
import { defaultSearchOptions, defaultGenerateOptions, searchMethodOptions } from "@/constants/chatConfig";

const router = useRouter();

const sessions = ref([]);
const loading = ref(false);
const showCreateModal = ref(false);
const saving = ref(false);
const editingSession = ref(null);

const knowledgeBases = ref([]);
const loadingKbs = ref(false);
const fileList = ref([]);

const sessionForm = ref({
  name: "",
  icon: "",
  description: "你是一位智能助手。",
  kb_ids: [],
  search_options: { ...defaultSearchOptions },
  generate_options: { ...defaultGenerateOptions }
});

// 加载知识库列表
const loadKnowledgeBases = async () => {
  loadingKbs.value = true;
  try {
    const res = await getKnowledgeBases();
    knowledgeBases.value = res.knowledge_bases || [];
  } catch (e) {
    message.error("加载知识库失败");
  } finally {
    loadingKbs.value = false;
  }
};

// 头像上传前检查
const beforeUpload = file => {
  const isLt4M = file.size / 1024 / 1024 < 4;
  if (!isLt4M) {
    message.error("图片大小不能超过 4MB!");
    return false;
  }
  return false;
};

// 处理头像变化
const handleAvatarChange = info => {
  if (info.fileList.length > 0) {
    const file = info.fileList[0].originFileObj;
    const reader = new FileReader();
    reader.onload = e => {
      sessionForm.value.icon = e.target.result;
    };
    reader.readAsDataURL(file);
  } else {
    sessionForm.value.icon = "";
  }
};

// 取消弹窗
const handleCancel = () => {
  showCreateModal.value = false;
  editingSession.value = null;
  fileList.value = [];
  sessionForm.value = {
    name: "",
    icon: "",
    description: "你是一位智能助手。",
    kb_ids: [],
    search_options: { ...defaultSearchOptions },
    generate_options: { ...defaultGenerateOptions }
  };
};

// 加载会话列表
const loadSessions = async () => {
  loading.value = true;
  try {
    const res = await getChatApps();
    sessions.value = res.apps || [];
  } catch (e) {
    message.error("加载助手列表失败");
    console.error(e);
  } finally {
    loading.value = false;
  }
};

/** 进入助手详情页 */
const goToChat = session => {
  router.push({
    path: "/chat/detail",
    query: { app_session_key: session.session_key }
  });
};

/** 编辑助手：打开弹窗前从数据库拉取最新配置和知识库列表，保证展示的是最新数据 */
const editSession = async session => {
  editingSession.value = session;
  try {
    const [app] = await Promise.all([getChatAppDetail(session.session_key), loadKnowledgeBases()]);
    sessionForm.value = {
      name: app.name || "",
      icon: app.icon || "",
      description: app.description || "你是一位智能助手。",
      kb_ids: app.kb_ids || [],
      search_options: { ...defaultSearchOptions, ...app.search_options },
      generate_options: { ...defaultGenerateOptions, ...app.generate_options }
    };
    editingSession.value = app;
    if (app.icon) {
      fileList.value = [{ uid: "-1", name: "avatar.png", status: "done", url: app.icon }];
    } else {
      fileList.value = [];
    }
    showCreateModal.value = true;
  } catch (e) {
    message.error("加载配置失败");
  }
};

// 保存会话
const handleSaveSession = async () => {
  if (!sessionForm.value.name) {
    message.warning("请输入助手名称");
    return;
  }

  saving.value = true;

  try {
    if (editingSession.value) {
      // 更新
      await updateChatApp(editingSession.value.session_key, sessionForm.value);
      message.success("更新成功");
    } else {
      // 创建助手
      const res = await createChatApp(sessionForm.value);
      message.success("创建成功");
      router.push({
        path: "/chat/detail",
        query: { app_session_key: res.session_key }
      });
    }

    await loadSessions();
    handleCancel();
  } catch (e) {
    message.error(editingSession.value ? "更新失败" : "创建失败");
    console.error(e);
  } finally {
    saving.value = false;
  }
};

// 删除会话
const confirmDelete = session => {
  Modal.confirm({
    title: "确认删除",
    content: `确定要删除助手「${session.name}」吗？`,
    okText: "删除",
    okType: "danger",
    async onOk() {
      try {
        await deleteChatApp(session.session_key);
        message.success("删除成功");
        await loadSessions();
      } catch (e) {
        message.error("删除失败");
        console.error(e);
      }
    }
  });
};

// 截断文本
const truncate = (text, len) => {
  if (!text) return "";
  return text.length > len ? text.slice(0, len) + "..." : text;
};

// 格式化日期
const formatDate = dateStr => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return "今天";
  if (days === 1) return "昨天";
  if (days < 7) return `${days}天前`;
  return date.toLocaleDateString("zh-CN");
};

onMounted(() => {
  loadKnowledgeBases();
  loadSessions();
});
</script>

<style scoped lang="scss">
.chat-container {
  padding: 15px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #262626;
  margin-bottom: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;

  .header-left {
    display: flex;
    gap: 12px;
    align-items: center;
  }
}

.empty-state {
  padding: 80px 0;
  color: #8c8c8c;
  text-align: center;

  h3 {
    margin: 20px 0 8px;
    color: #262626;
  }

  p {
    margin-bottom: 24px;
  }
}

.session-click-area {
  cursor: pointer;
}

.session-card {
  position: relative;
  margin-bottom: 20px;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 8px 24px rgb(0 0 0 / 12%);
    transform: translateY(-4px);
  }

  .session-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    color: white;
    margin-bottom: 16px;
  }

  .session-info {
    .session-title {
      margin: 0 0 8px;
      font-size: 16px;
      font-weight: 600;
      color: #262626;
    }

    .session-summary {
      min-height: 40px;
      margin: 0 0 12px;
      font-size: 13px;
      color: #8c8c8c;
    }

    .session-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;

      .session-time {
        font-size: 12px;
        color: #bfbfbf;
      }
    }
  }

  .session-actions {
    position: absolute;
    top: 16px;
    right: 16px;
  }
}
</style>
