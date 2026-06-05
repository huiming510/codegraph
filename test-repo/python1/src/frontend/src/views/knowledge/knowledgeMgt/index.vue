<template>
  <div class="knowledge-container">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 style="display: flex; gap: 10px; align-items: center; margin: 0">
          <FolderOutlined style="color: #667eea" />
          知识库管理
        </h2>
        <a-tag color="purple">{{ knowledgeBases.length }} 个知识库</a-tag>
      </div>
      <a-button
        type="primary"
        @click="openCreateModal"
        style="background: linear-gradient(135deg, #667eea, #764ba2); border: none"
      >
        <PlusOutlined /> 新建知识库
      </a-button>
    </div>

    <!-- 主体：左侧大纲树 + 右侧列表 -->
    <a-spin :spinning="loading">
      <div v-if="knowledgeBases.length === 0" class="empty-state">
        <FolderOpenOutlined style="font-size: 64px; color: #d9d9d9" />
        <h3>暂无知识库</h3>
        <p>创建您的第一个知识库，开始管理文档</p>
        <a-button type="primary" @click="openCreateModal"> <PlusOutlined /> 新建知识库 </a-button>
      </div>

      <a-row v-else :gutter="20">
        <a-col :span="24">
          <a-row :gutter="20">
            <a-col :span="8" v-for="kb in knowledgeBases" :key="kb.id">
              <a-card :bordered="false" class="kb-card card-hover" @click="goToKnowledgeBase(kb)">
                <div class="kb-icon" :style="{ background: kb.color }">
                  {{ kb.icon }}
                </div>
                <div class="kb-info">
                  <h3 class="kb-name">{{ kb.name }}</h3>
                  <p class="kb-desc">{{ kb.description || "暂无描述" }}</p>
                  <div class="kb-meta">
                    <a-tag color="blue">{{ kb.document_count }} 个文档</a-tag>
                    <span class="kb-time">{{ formatDate(kb.created_at) }}</span>
                  </div>
                </div>
                <div class="kb-actions" @click.stop>
                  <a-dropdown>
                    <a-button type="text" size="small">
                      <MoreOutlined />
                    </a-button>
                    <template #overlay>
                      <a-menu>
                        <a-menu-item @click="editKnowledgeBase(kb)"> <EditOutlined /> 编辑 </a-menu-item>
                        <a-menu-item danger @click="confirmDelete(kb)"> <DeleteOutlined /> 删除 </a-menu-item>
                      </a-menu>
                    </template>
                  </a-dropdown>
                </div>
              </a-card>
            </a-col>
          </a-row>
        </a-col>
      </a-row>
    </a-spin>

    <!-- 创建/编辑知识库弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      :title="editingKb ? '编辑知识库' : '新建知识库'"
      @ok="handleSaveKnowledgeBase"
      :confirm-loading="saving"
    >
      <a-form :model="kbForm" layout="vertical">
        <a-form-item label="知识库名称" required>
          <a-input v-model:value="kbForm.name" placeholder="请输入知识库名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="kbForm.description" placeholder="请输入描述（可选）" :rows="3" />
        </a-form-item>
        <a-form-item label="图标">
          <div class="icon-picker">
            <span
              v-for="icon in iconOptions"
              :key="icon"
              :class="['icon-option', { active: kbForm.icon === icon }]"
              @click="kbForm.icon = icon"
            >
              {{ icon }}
            </span>
          </div>
        </a-form-item>
        <a-form-item label="主题色">
          <div class="color-picker">
            <span
              v-for="color in colorOptions"
              :key="color"
              :class="['color-option', { active: kbForm.color === color }]"
              :style="{ background: color }"
              @click="kbForm.color = color"
            />
          </div>
        </a-form-item>
        <a-form-item label="chunk_size" required>
          <a-input-number v-model:value="kbForm.chunk_size" :min="1" :step="128" style="width: 100%" />
        </a-form-item>
        <a-form-item label="chunk_overlap" required>
          <a-input-number v-model:value="kbForm.chunk_overlap" :min="0" :step="32" style="width: 100%" />
        </a-form-item>
        <a-form-item label="chunk_strategy" required>
          <a-input v-model:value="kbForm.chunk_strategy" placeholder="如 general" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { message, Modal } from "ant-design-vue";
import {
  FolderOutlined,
  FolderOpenOutlined,
  PlusOutlined,
  MoreOutlined,
  EditOutlined,
  DeleteOutlined
} from "@ant-design/icons-vue";
import { getKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from "@/api/modules/knowledgeBase";

const router = useRouter();

const knowledgeBases = ref([]);
const loading = ref(false);
const showCreateModal = ref(false);
const saving = ref(false);
const editingKb = ref(null);

const kbForm = ref({
  name: "",
  description: "",
  icon: "📚",
  color: "#667eea",
  chunk_size: 4096,
  chunk_overlap: 256,
  chunk_strategy: "general"
});

const iconOptions = ["📚", "📖", "📁", "💼", "🎯", "🔬", "💡", "🚀", "⚙️", "📊", "🎨", "🔧"];
const colorOptions = ["#667eea", "#764ba2", "#52c41a", "#faad14", "#13c2c2", "#eb2f96", "#722ed1", "#2f54eb"];
const loadKnowledgeBases = async () => {
  loading.value = true;
  try {
    const res = await getKnowledgeBases();
    knowledgeBases.value = res.knowledge_bases || [];
  } catch (e) {
    message.error("加载失败");
  } finally {
    loading.value = false;
  }
};

const goToKnowledgeBase = kb => {
  router.push(`/knowledge/documentMgt?kb=${kb.id}`);
};

const openCreateModal = () => {
  editingKb.value = null;
  kbForm.value = {
    name: "",
    description: "",
    icon: "📚",
    color: "#667eea",
    chunk_size: 4096,
    chunk_overlap: 256,
    chunk_strategy: "general"
  };
  showCreateModal.value = true;
};

const editKnowledgeBase = kb => {
  editingKb.value = kb;
  kbForm.value = {
    name: kb.name,
    description: kb.description || "",
    icon: kb.icon,
    color: kb.color,
    chunk_size: kb.chunk_size ?? 4096,
    chunk_overlap: kb.chunk_overlap ?? 256,
    chunk_strategy: kb.chunk_strategy || "general"
  };
  showCreateModal.value = true;
};

const handleSaveKnowledgeBase = async () => {
  if (!kbForm.value.name.trim()) {
    message.warning("请输入知识库名称");
    return;
  }
  if ((kbForm.value.chunk_size ?? 0) <= 0) {
    message.warning("chunk_size 必须大于 0");
    return;
  }
  if ((kbForm.value.chunk_overlap ?? -1) < 0) {
    message.warning("chunk_overlap 不能小于 0");
    return;
  }
  if ((kbForm.value.chunk_overlap ?? 0) >= (kbForm.value.chunk_size ?? 0)) {
    message.warning("chunk_overlap 必须小于 chunk_size");
    return;
  }
  if (!String(kbForm.value.chunk_strategy || "").trim()) {
    message.warning("chunk_strategy 不能为空");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: kbForm.value.name,
      description: kbForm.value.description,
      icon: kbForm.value.icon,
      color: kbForm.value.color,
      chunk_size: Number(kbForm.value.chunk_size),
      chunk_overlap: Number(kbForm.value.chunk_overlap),
      chunk_strategy: String(kbForm.value.chunk_strategy).trim()
    };
    if (editingKb.value) {
      await updateKnowledgeBase(editingKb.value.id, payload);
      message.success("更新成功");
    } else {
      await createKnowledgeBase(payload);
      message.success("创建成功");
    }
    showCreateModal.value = false;
    editingKb.value = null;
    kbForm.value = {
      name: "",
      description: "",
      icon: "📚",
      color: "#667eea",
      chunk_size: 4096,
      chunk_overlap: 256,
      chunk_strategy: "general"
    };
    loadKnowledgeBases();
  } catch (e) {
    message.error("操作失败");
  } finally {
    saving.value = false;
  }
};

const confirmDelete = kb => {
  Modal.confirm({
    title: "确认删除",
    content: `确定要删除知识库「${kb.name}」吗？该操作将同时删除所有相关文档。`,
    okText: "删除",
    okType: "danger",
    async onOk() {
      try {
        const res = await deleteKnowledgeBase(kb.id);
        if (res?.linkrag_not_configured) {
          message.warning(
            "删除成功，但未配置 linkrag_server_url (.env)，解析服务索引未被删除，配置后需手动清理"
          );
        } else {
          message.success("删除成功");
        }
        loadKnowledgeBases();
      } catch (e) {
        message.error("删除失败");
      }
    }
  });
};

const formatDate = dateStr => {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("zh-CN");
};

onMounted(loadKnowledgeBases);
</script>

<style scoped lang="scss">
.knowledge-container {
  padding: 15px;
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

.kb-card {
  position: relative;
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 8px 24px rgb(0 0 0 / 12%);
    transform: translateY(-4px);
  }

  .kb-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    margin-bottom: 16px;
    font-size: 28px;
    border-radius: 12px;
  }

  .kb-info {
    .kb-name {
      margin: 0 0 8px;
      font-size: 16px;
      font-weight: 600;
      color: #262626;
    }

    .kb-desc {
      margin: 0 0 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 13px;
      color: #8c8c8c;
      white-space: nowrap;
    }

    .kb-meta {
      display: flex;
      gap: 8px;
      align-items: center;

      .kb-time {
        font-size: 12px;
        color: #bfbfbf;
      }
    }
  }

  .kb-actions {
    position: absolute;
    top: 16px;
    right: 16px;
  }
}

.icon-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  .icon-option {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    font-size: 20px;
    cursor: pointer;
    border: 2px solid #f0f0f0;
    border-radius: 8px;
    transition: all 0.2s;

    &:hover {
      border-color: #667eea;
    }

    &.active {
      background: rgb(102 126 234 / 10%);
      border-color: #667eea;
    }
  }
}

.color-picker {
  display: flex;
  gap: 8px;

  .color-option {
    width: 32px;
    height: 32px;
    cursor: pointer;
    border: 3px solid transparent;
    border-radius: 50%;
    transition: all 0.2s;

    &:hover {
      transform: scale(1.1);
    }

    &.active {
      border-color: #262626;
    }
  }
}

.custom-parse-methods {
  margin-top: 8px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}
</style>
