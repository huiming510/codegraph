<template>
  <div class="system-logs inner-page-card">
    <!-- 统计卡片 -->
    <a-row :gutter="20" style="margin-bottom: 20px">
      <a-col :span="6">
        <a-card :bordered="false" class="card-hover stat-card">
          <a-statistic title="今日查询" :value="stats.todayQueries" :value-style="{ color: '#667eea' }">
            <template #prefix><SearchOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="false" class="card-hover stat-card">
          <a-statistic title="成功率" :value="stats.successRate" suffix="%" :value-style="{ color: '#52c41a' }">
            <template #prefix><CheckCircleOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="false" class="card-hover stat-card">
          <a-statistic title="平均耗时" :value="stats.avgLatency" suffix="ms" :value-style="{ color: '#faad14' }">
            <template #prefix><ClockCircleOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="false" class="card-hover stat-card">
          <a-statistic title="错误数" :value="stats.errorCount" :value-style="{ color: '#ff4d4f' }">
            <template #prefix><WarningOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="20">
      <!-- 查询日志 -->
      <a-col :span="24" style="margin-bottom: 20px">
        <a-card :bordered="false" class="card-hover">
          <template #title>
            <div style="display: flex; gap: 10px; align-items: center">
              <div
                style="
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  width: 32px;
                  height: 32px;
                  background: linear-gradient(135deg, #667eea, #764ba2);
                  border-radius: 8px;
                "
              >
                <SearchOutlined style="font-size: 16px; color: white" />
              </div>
              <span>查询日志</span>
              <a-tag color="purple">{{ queryLogs.length }} 条</a-tag>
            </div>
          </template>
          <template #extra>
            <a-space>
              <a-select v-model:value="queryFilter" style="width: 120px" @change="loadQueryLogs">
                <a-select-option value="all">全部</a-select-option>
                <a-select-option value="success">成功</a-select-option>
                <a-select-option value="failed">失败</a-select-option>
              </a-select>
              <a-button type="text" @click="loadQueryLogs">
                <ReloadOutlined :class="{ 'icon-spin': loadingQuery }" />
              </a-button>
            </a-space>
          </template>

          <a-table
            :columns="queryColumns"
            :data-source="queryLogs"
            :loading="loadingQuery"
            :pagination="{ pageSize: 10, showSizeChanger: true, showTotal: total => `共 ${total} 条` }"
            row-key="id"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'query'">
                <a-tooltip :title="record.query">
                  <span style="cursor: pointer">{{ truncate(record.query, 50) }}</span>
                </a-tooltip>
              </template>
              <template v-if="column.key === 'answer'">
                <a-tooltip :title="record.answer">
                  <span style="color: #8c8c8c">{{ truncate(record.answer, 40) }}</span>
                </a-tooltip>
              </template>
              <template v-if="column.key === 'success'">
                <a-tag :color="record.success ? 'green' : 'red'">
                  {{ record.success ? "成功" : "失败" }}
                </a-tag>
              </template>
              <template v-if="column.key === 'latency_ms'">
                <span :style="{ color: record.latency_ms > 3000 ? '#ff4d4f' : record.latency_ms > 1000 ? '#faad14' : '#52c41a' }">
                  {{ record.latency_ms }}ms
                </span>
              </template>
              <template v-if="column.key === 'created_at'">
                {{ formatTime(record.created_at) }}
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>

      <!-- 系统日志 -->
      <a-col :span="24">
        <a-card :bordered="false" class="card-hover">
          <template #title>
            <div style="display: flex; gap: 10px; align-items: center">
              <div
                style="
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  width: 32px;
                  height: 32px;
                  background: linear-gradient(135deg, #52c41a, #389e0d);
                  border-radius: 8px;
                "
              >
                <FileTextOutlined style="font-size: 16px; color: white" />
              </div>
              <span>系统日志</span>
              <a-tag color="blue">{{ systemLogs.length }} 条</a-tag>
            </div>
          </template>
          <template #extra>
            <a-space>
              <a-select v-model:value="levelFilter" style="width: 120px" @change="loadSystemLogs">
                <a-select-option value="all">全部级别</a-select-option>
                <a-select-option value="DEBUG">DEBUG</a-select-option>
                <a-select-option value="INFO">INFO</a-select-option>
                <a-select-option value="WARNING">WARNING</a-select-option>
                <a-select-option value="ERROR">ERROR</a-select-option>
              </a-select>
              <a-button type="text" @click="loadSystemLogs">
                <ReloadOutlined :class="{ 'icon-spin': loadingSystem }" />
              </a-button>
            </a-space>
          </template>

          <a-table
            :columns="systemColumns"
            :data-source="systemLogs"
            :loading="loadingSystem"
            :pagination="{ pageSize: 10, showSizeChanger: true, showTotal: total => `共 ${total} 条` }"
            row-key="id"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'level'">
                <a-tag :color="getLevelColor(record.level)">
                  {{ record.level }}
                </a-tag>
              </template>
              <template v-if="column.key === 'module'">
                <span style="font-family: monospace; font-size: 12px; color: #667eea">
                  {{ record.module }}
                </span>
              </template>
              <template v-if="column.key === 'message'">
                <a-tooltip :title="record.message">
                  <span>{{ truncate(record.message, 80) }}</span>
                </a-tooltip>
              </template>
              <template v-if="column.key === 'created_at'">
                {{ formatTime(record.created_at) }}
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { message } from "ant-design-vue";
import {
  SearchOutlined,
  FileTextOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined
} from "@ant-design/icons-vue";
import { getQueryLogs, getSystemLogs } from "@/api/modules/logs";

const queryLogs = ref([]);
const systemLogs = ref([]);
const loadingQuery = ref(false);
const loadingSystem = ref(false);
const queryFilter = ref("all");
const levelFilter = ref("all");

// 查询日志表格列
const queryColumns = [
  { title: "ID", dataIndex: "id", key: "id", width: 60 },
  { title: "查询内容", dataIndex: "query", key: "query" },
  { title: "回答摘要", dataIndex: "answer", key: "answer" },
  { title: "状态", dataIndex: "success", key: "success", width: 80 },
  { title: "耗时", dataIndex: "latency_ms", key: "latency_ms", width: 100 },
  { title: "时间", dataIndex: "created_at", key: "created_at", width: 160 }
];

// 系统日志表格列
const systemColumns = [
  { title: "ID", dataIndex: "id", key: "id", width: 60 },
  { title: "级别", dataIndex: "level", key: "level", width: 100 },
  { title: "模块", dataIndex: "module", key: "module", width: 150 },
  { title: "消息", dataIndex: "message", key: "message" },
  { title: "时间", dataIndex: "created_at", key: "created_at", width: 160 }
];

// 统计数据
const stats = computed(() => {
  const successCount = queryLogs.value.filter(l => l.success).length;
  const totalCount = queryLogs.value.length;
  const totalLatency = queryLogs.value.reduce((sum, l) => sum + (l.latency_ms || 0), 0);
  const errorCount = systemLogs.value.filter(l => l.level === "ERROR").length;

  return {
    todayQueries: totalCount,
    successRate: totalCount > 0 ? Math.round((successCount / totalCount) * 100) : 0,
    avgLatency: totalCount > 0 ? Math.round(totalLatency / totalCount) : 0,
    errorCount
  };
});

// 加载查询日志
const loadQueryLogs = async () => {
  loadingQuery.value = true;
  try {
    const params = {};
    if (queryFilter.value === "success") params.success = true;
    else if (queryFilter.value === "failed") params.success = false;

    const response = await getQueryLogs(params);
    queryLogs.value = response.logs || [];
  } catch (error) {
    message.error("加载查询日志失败");
  } finally {
    loadingQuery.value = false;
  }
};

// 加载系统日志
const loadSystemLogs = async () => {
  loadingSystem.value = true;
  try {
    const params = {};
    if (levelFilter.value !== "all") params.level = levelFilter.value;

    const response = await getSystemLogs(params);
    systemLogs.value = response.logs || [];
  } catch (error) {
    message.error("加载系统日志失败");
  } finally {
    loadingSystem.value = false;
  }
};

// 截断文本
const truncate = (text, length) => {
  if (!text) return "-";
  return text.length > length ? text.slice(0, length) + "..." : text;
};

// 格式化时间
const formatTime = timeStr => {
  if (!timeStr) return "-";
  return new Date(timeStr).toLocaleString("zh-CN");
};

// 获取日志级别颜色
const getLevelColor = level => {
  const colors = {
    DEBUG: "default",
    INFO: "blue",
    WARNING: "orange",
    ERROR: "red",
    CRITICAL: "purple"
  };
  return colors[level] || "default";
};

onMounted(() => {
  loadQueryLogs();
  loadSystemLogs();
});
</script>

<style scoped>
.system-logs {
  height: 100%;
  overflow: hidden;
  overflow: auto;
}

.stat-card {
  text-align: center;
}

.stat-card :deep(.ant-statistic-title) {
  font-size: 14px;
  color: #8c8c8c;
}

.icon-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}
</style>
