<template>
  <div class="inner-page-card user-mgt-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <div class="header-icon">
          <TeamOutlined />
        </div>
        <div class="header-info">
          <h2>用户管理</h2>
          <p>管理系统用户与知识库角色（管理员 / 开发人员 / 用户）</p>
        </div>
      </div>
      <a-button type="primary" @click="handleAdd"> <PlusOutlined /> 添加用户 </a-button>
    </div>

    <!-- 统计卡片：总用户、活跃、管理员/开发人员/用户 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea, #764ba2)">
          <TeamOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总用户数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #52c41a, #73d13d)">
          <UserOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.active }}</div>
          <div class="stat-label">活跃用户</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #faad14, #ffc53d)">
          <CrownOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.admins }}</div>
          <div class="stat-label">管理员</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #1890ff, #40a9ff)">
          <CodeOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.developers }}</div>
          <div class="stat-label">开发人员</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #8c8c8c, #bfbfbf)">
          <TeamOutlined />
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.guests }}</div>
          <div class="stat-label">用户</div>
        </div>
      </div>
    </div>

    <!-- 用户列表 -->
    <div class="table-card">
      <a-table :columns="columns" :data-source="users" :loading="loading" :pagination="{ pageSize: 10 }" row-key="id">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'nickname'">
            <div class="user-cell">
              <div class="user-avatar">{{ record.nickname?.charAt(0) || "U" }}</div>
              <div>
                <div class="user-name">{{ record.nickname }}</div>
                <div class="user-username">@{{ record.username }}</div>
              </div>
            </div>
          </template>
          <template v-else-if="column.key === 'role'">
            <a-tag :color="roleColors[record.role]">{{ roleLabels[record.role] }}</a-tag>
          </template>
          <template v-else-if="column.key === 'is_active'">
            <a-tag :color="record.is_active ? 'green' : 'red'">
              {{ record.is_active ? "正常" : "禁用" }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'last_login'">
            {{ record.last_login ? formatTime(record.last_login) : "从未登录" }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleEdit(record)"> <EditOutlined /> 编辑 </a-button>
              <a-popconfirm title="确定将该用户密码重置为 123456 吗？" @confirm="handleResetPassword(record)">
                <a-button type="link" size="small"> <KeyOutlined /> 重置密码 </a-button>
              </a-popconfirm>
              <a-popconfirm title="确定要删除此用户吗？" @confirm="handleDelete(record.id)" :disabled="record.role === 'admin'">
                <a-button type="link" size="small" danger :disabled="record.role === 'admin'"> <DeleteOutlined /> 删除 </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 添加/编辑用户弹窗 -->
    <a-modal v-model:open="showModal" :title="editingUser ? '编辑用户' : '添加用户'" @ok="handleSave" :confirm-loading="saving">
      <a-form :model="userForm" layout="vertical">
        <a-form-item label="用户名" :rules="[{ required: true }]">
          <a-input v-model:value="userForm.username" :disabled="!!editingUser" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item v-if="!editingUser" label="密码" :rules="[{ required: true }]">
          <a-input-password v-model:value="userForm.password" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item label="昵称">
          <a-input v-model:value="userForm.nickname" placeholder="请输入昵称" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model:value="userForm.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item label="角色">
          <a-select v-model:value="userForm.role">
            <a-select-option value="admin">管理员</a-select-option>
            <a-select-option value="user">开发人员</a-select-option>
            <a-select-option value="guest">用户</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="editingUser" label="状态">
          <a-switch v-model:checked="userForm.is_active" checked-children="正常" un-checked-children="禁用" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { message } from "ant-design-vue";
import {
  TeamOutlined,
  UserOutlined,
  CrownOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CodeOutlined,
  KeyOutlined
} from "@ant-design/icons-vue";
import { getUserListApi, createUserApi, updateUserApi, deleteUserApi, resetPasswordApi } from "@/api/modules/user";

const loading = ref(false);
const saving = ref(false);
const users = ref([]);
const showModal = ref(false);
const editingUser = ref(null);
const userForm = ref({
  username: "",
  password: "",
  nickname: "",
  email: "",
  role: "user",
  is_active: true
});

// 与后端鉴权中心一致：admin=管理员，user=开发人员，guest=用户
const roleLabels = {
  admin: "管理员",
  user: "开发人员",
  guest: "用户"
};

const roleColors = {
  admin: "purple",
  user: "blue",
  guest: "default"
};

const columns = [
  { title: "用户", key: "nickname", dataIndex: "nickname" },
  { title: "邮箱", key: "email", dataIndex: "email" },
  { title: "角色", key: "role", dataIndex: "role" },
  { title: "状态", key: "is_active", dataIndex: "is_active" },
  { title: "最后登录", key: "last_login", dataIndex: "last_login" },
  { title: "操作", key: "action", width: 240 }
];

const stats = computed(() => ({
  total: users.value.length,
  active: users.value.filter(u => u.is_active).length,
  admins: users.value.filter(u => u.role === "admin").length,
  developers: users.value.filter(u => u.role === "user").length,
  guests: users.value.filter(u => u.role === "guest").length
}));

const formatTime = time => {
  if (!time) return "";
  return new Date(time).toLocaleString("zh-CN");
};

const loadUsers = async () => {
  loading.value = true;
  try {
    const res = await getUserListApi();
    users.value = res.users || res.data?.users || [];
  } catch (e) {
    message.error("加载用户列表失败");
  } finally {
    loading.value = false;
  }
};

const handleAdd = () => {
  editingUser.value = null;
  userForm.value = { username: "", password: "", nickname: "", email: "", role: "user", is_active: true };
  showModal.value = true;
};

const handleEdit = user => {
  editingUser.value = user;
  userForm.value = {
    username: user.username,
    password: "",
    nickname: user.nickname,
    email: user.email,
    role: user.role,
    is_active: user.is_active
  };
  showModal.value = true;
};

const handleSave = async () => {
  saving.value = true;
  try {
    if (editingUser.value) {
      await updateUserApi(editingUser.value.id, {
        nickname: userForm.value.nickname,
        email: userForm.value.email,
        role: userForm.value.role,
        is_active: userForm.value.is_active
      });
      message.success("用户更新成功");
    } else {
      await createUserApi({
        username: userForm.value.username,
        password: userForm.value.password,
        nickname: userForm.value.nickname,
        email: userForm.value.email,
        role: userForm.value.role
      });
      message.success("用户创建成功");
    }
    showModal.value = false;
    loadUsers();
  } catch (e) {
    message.error(e.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
};

const handleDelete = async userId => {
  try {
    await deleteUserApi(userId);
    message.success("用户删除成功");
    loadUsers();
  } catch (e) {
    message.error(e.response?.data?.detail || "删除失败");
  }
};

/** 管理员重置用户密码为 123456 */
const handleResetPassword = async record => {
  try {
    await resetPasswordApi(record.id, "123456");
    message.success(`已将 ${record.nickname || record.username} 的密码重置为 123456`);
  } catch (e) {
    message.error(e.response?.data?.detail || "重置密码失败");
  }
};

onMounted(() => {
  loadUsers();
});
</script>

<style scoped lang="scss">
.user-mgt-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  overflow: auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  gap: 16px;
  align-items: center;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  font-size: 24px;
  color: #ffffff;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 12px;
}

.header-info {
  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }

  p {
    margin: 4px 0 0;
    font-size: 14px;
    color: #8c8c8c;
  }
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 20px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgb(0 0 0 / 6%);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  font-size: 22px;
  color: #ffffff;
  border-radius: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #262626;
}

.stat-label {
  font-size: 14px;
  color: #8c8c8c;
}

.table-card {
  height: 100%;
  padding: 20px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgb(0 0 0 / 6%);
}

.user-cell {
  display: flex;
  gap: 12px;
  align-items: center;
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 50%;
}

.user-name {
  font-weight: 500;
}

.user-username {
  font-size: 12px;
  color: #8c8c8c;
}
</style>
