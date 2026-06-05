<template>
  <div class="home-container">
    <!-- 顶部统计卡片：按角色显示（guest 仅查询/对话，user 含文档，admin 含活跃用户） -->
    <a-row :gutter="20" class="stats-row">
      <a-col v-if="showStats.document" :span="statsColSpan">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon stat-icon--doc">
              <FileTextOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.documentCount }}</div>
              <div class="stat-label">知识库文档</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="trend up"><ArrowUpOutlined /> 12%</span>
            <span>较上周</span>
          </div>
        </a-card>
      </a-col>
      <a-col :span="statsColSpan">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon stat-icon--query">
              <SearchOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.queryCount }}</div>
              <div class="stat-label">今日查询</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="trend up"><ArrowUpOutlined /> 8%</span>
            <span>较昨日</span>
          </div>
        </a-card>
      </a-col>
      <a-col :span="statsColSpan">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon stat-icon--chat">
              <MessageOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.chatCount }}</div>
              <div class="stat-label">对话次数</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="trend up"><ArrowUpOutlined /> 23%</span>
            <span>较昨日</span>
          </div>
        </a-card>
      </a-col>
      <a-col v-if="showStats.user" :span="statsColSpan">
        <a-card :bordered="false" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon stat-icon--user">
              <TeamOutlined />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.userCount }}</div>
              <div class="stat-label">活跃用户</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="trend up"><ArrowUpOutlined /> 5%</span>
            <span>较上周</span>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="20" class="content-row">
      <!-- 左侧：快捷入口 + 最近查询 -->
      <a-col :span="16" class="content-col content-col--left">
        <!-- 快捷入口 -->
        <a-card :bordered="false" class="card-hover card-mb">
          <template #title>
            <div class="card-title">
              <AppstoreOutlined />
              <span>快捷入口</span>
            </div>
          </template>
          <a-row :gutter="16">
            <a-col :span="6" v-for="item in visibleQuickLinks" :key="item.path">
              <div class="quick-link" @click="$router.push(item.path)">
                <div class="quick-icon" :style="{ background: item.color }">
                  <component :is="item.icon" />
                </div>
                <div class="quick-text">{{ item.title }}</div>
              </div>
            </a-col>
          </a-row>
        </a-card>

        <!-- 最近查询 -->
        <a-card :bordered="false" class="card-hover card-scroll">
          <template #title>
            <div class="card-title">
              <HistoryOutlined />
              <span>最近查询</span>
            </div>
          </template>
          <template #extra>
            <a-button type="link" @click="$router.push('/query/rag')">查看更多</a-button>
          </template>
          <div class="card-scroll-body">
            <a-table :columns="queryColumns" :data-source="recentQueries" :pagination="false" size="middle">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'query'">
                  <a-tooltip :title="record.query">
                    {{ truncate(record.query, 40) }}
                  </a-tooltip>
                </template>
                <template v-if="column.key === 'status'">
                  <a-tag :color="record.success ? 'green' : 'red'">
                    {{ record.success ? "成功" : "失败" }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'latency'">
                  <span :class="{ 'latency-ok': record.latency <= 2000, 'latency-slow': record.latency > 2000 }">
                    {{ record.latency }}ms
                  </span>
                </template>
              </template>
            </a-table>
          </div>
        </a-card>
      </a-col>

      <!-- 右侧：系统状态（仅 admin）+ 最近上传（user/admin） -->
      <a-col :span="8" class="content-col content-col--right">
        <!-- 系统状态：仅管理员可见 -->
        <a-card v-if="showSystemStatus" :bordered="false" class="card-hover card-mb card-scroll">
          <template #title>
            <div class="card-title">
              <DashboardOutlined />
              <span>系统状态</span>
            </div>
          </template>
          <div class="card-scroll-body">
            <div class="system-status">
              <div class="status-item">
                <div class="status-label">LLM 服务</div>
                <a-tag :color="systemStatus.llm ? 'green' : 'red'">
                  {{ systemStatus.llm ? "正常" : "异常" }}
                </a-tag>
              </div>
              <div class="status-item">
                <div class="status-label">向量数据库</div>
                <a-tag :color="systemStatus.vectorDb ? 'green' : 'red'">
                  {{ systemStatus.vectorDb ? "正常" : "异常" }}
                </a-tag>
              </div>
              <div class="status-item">
                <div class="status-label">MySQL 数据库</div>
                <a-tag :color="systemStatus.mysql ? 'green' : 'red'">
                  {{ systemStatus.mysql ? "正常" : "异常" }}
                </a-tag>
              </div>
              <div class="status-item">
                <div class="status-label">当前模型</div>
                <a-tag color="purple">{{ systemStatus.model }}</a-tag>
              </div>
            </div>
          </div>
        </a-card>

        <!-- 最近上传：开发人员与管理員可见 -->
        <a-card v-if="showRecentUpload" :bordered="false" class="card-hover card-scroll">
          <template #title>
            <div class="card-title">
              <CloudUploadOutlined />
              <span>最近上传</span>
            </div>
          </template>
          <template #extra>
            <a-button type="link" @click="$router.push('/knowledge/upload')">查看更多</a-button>
          </template>
          <div class="card-scroll-body">
            <div class="recent-docs">
              <div v-for="doc in recentDocs" :key="doc.id" class="doc-item">
                <FileTextOutlined class="doc-item-icon" />
                <div class="doc-info">
                  <div class="doc-name">{{ truncate(doc.filename, 20) }}</div>
                  <div class="doc-time">{{ doc.time }}</div>
                </div>
                <a-tag color="green" size="small">已入库</a-tag>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
/**
 * 首页：按用户角色展示不同内容
 * - guest：仅今日查询、对话次数、快捷入口（智能问答、智能检索）、最近查询
 * - user（开发人员）：含知识库文档统计、工作流/知识库/文档管理入口、最近上传，不含活跃用户与系统状态
 * - admin：全部统计、全部快捷入口、系统状态、最近上传
 */
import { ref, computed, onMounted } from "vue";
import {
  FileTextOutlined,
  SearchOutlined,
  MessageOutlined,
  TeamOutlined,
  ArrowUpOutlined,
  AppstoreOutlined,
  HistoryOutlined,
  DashboardOutlined,
  CloudUploadOutlined,
  RobotOutlined,
  CommentOutlined,
  FolderOutlined,
  SettingOutlined
} from "@ant-design/icons-vue";
import { useUserStore } from "@/stores/modules/user";
import { getDocuments } from "@/api/modules/document";
import { getCurrentConfig } from "@/api/modules/llmConfig";

const userStore = useUserStore();
const role = computed(() => userStore.role || "guest");

// 按角色控制统计卡片显示：guest 不显示知识库文档与活跃用户，admin 全显示
const showStats = computed(() => ({
  document: role.value !== "guest",
  user: role.value === "admin"
}));
// 统计卡片列宽：guest 为 12（2 列），否则 6（4 列）
const statsColSpan = computed(() => (role.value === "guest" ? 12 : 6));

// 快捷入口全集；按角色过滤后使用
const quickLinksAll = [
  {
    title: "智能问答",
    path: "/chat/list",
    icon: CommentOutlined,
    color: "linear-gradient(135deg, #faad14, #d48806)",
    roles: ["admin", "user", "guest"]
  },
  {
    title: "工作流",
    path: "/workflow",
    icon: RobotOutlined,
    color: "linear-gradient(135deg, #722ed1, #531dab)",
    roles: ["admin", "user"]
  },
  {
    title: "知识库",
    path: "/knowledge/knowledgeMgt",
    icon: FolderOutlined,
    color: "linear-gradient(135deg, #52c41a, #389e0d)",
    roles: ["admin", "user"]
  },
  {
    title: "智能检索",
    path: "/query/rag",
    icon: SearchOutlined,
    color: "linear-gradient(135deg, #667eea, #764ba2)",
    roles: ["admin", "user", "guest"]
  },
  {
    title: "文档管理",
    path: "/AllDocumentMgt",
    icon: FolderOutlined,
    color: "linear-gradient(135deg, #1890ff, #096dd9)",
    roles: ["admin", "user"]
  },
  {
    title: "系统设置",
    path: "/system/llmConfig",
    icon: SettingOutlined,
    color: "linear-gradient(135deg, #13c2c2, #08979c)",
    roles: ["admin"]
  }
];
const visibleQuickLinks = computed(() => quickLinksAll.filter(item => item.roles.includes(role.value)));

// 仅管理员显示系统状态
const showSystemStatus = computed(() => role.value === "admin");
// 开发人员与管理員显示最近上传
const showRecentUpload = computed(() => role.value === "user" || role.value === "admin");

// 统计数据
const stats = ref({
  documentCount: 0,
  queryCount: 128,
  chatCount: 256,
  userCount: 12
});

// 最近查询
const queryColumns = [
  { title: "查询内容", dataIndex: "query", key: "query" },
  { title: "状态", dataIndex: "status", key: "status", width: 80 },
  { title: "耗时", dataIndex: "latency", key: "latency", width: 100 },
  { title: "时间", dataIndex: "time", key: "time", width: 100 }
];

const recentQueries = ref([
  { id: 1, query: "什么是 Python 编程语言？", success: true, latency: 523, time: "10:30" },
  { id: 2, query: "机器学习的主要类型有哪些？", success: true, latency: 892, time: "10:25" },
  { id: 3, query: "FastAPI 框架的特点是什么？", success: true, latency: 456, time: "10:20" },
  { id: 4, query: "Vue3 Composition API 使用方法", success: false, latency: 3200, time: "10:15" },
  { id: 5, query: "RAG 系统的工作原理", success: true, latency: 678, time: "10:10" }
]);

// 系统状态
const systemStatus = ref({
  llm: true,
  vectorDb: true,
  mysql: true,
  model: "Mock"
});

// 最近文档
const recentDocs = ref([]);

const truncate = (text, len) => (text?.length > len ? text.slice(0, len) + "..." : text);

const loadData = async () => {
  try {
    const r = role.value;
    // 非 guest 才请求文档（用于知识库文档数、最近上传）
    if (r !== "guest") {
      const docRes = await getDocuments();
      const docs = docRes.documents || [];
      stats.value.documentCount = docs.length;
      if (showRecentUpload.value) {
        recentDocs.value = docs.slice(0, 5).map(d => ({
          id: d.id,
          filename: d.filename,
          time: new Date(d.upload_time).toLocaleString("zh-CN", {
            month: "numeric",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit"
          })
        }));
      }
    }
    // 仅 admin 请求 LLM 配置（用于系统状态卡片）
    if (r === "admin") {
      const configRes = await getCurrentConfig();
      systemStatus.value.model = configRes.llm_model || "Mock";
    }
  } catch (e) {
    console.error("加载数据失败:", e);
  }
};

onMounted(loadData);
</script>

<style scoped lang="scss">
@use "./index.scss";
</style>
