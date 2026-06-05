<template>
  <div ref="listRef" class="app-list">
    <a-back-top :target="() => listRef" :right="50" :bottom="20" />
    <template v-for="item in data" :key="item.id">
      <a-card class="app-item" hoverable @click="toDetail(item)">
        <div class="app-item-header">
          <img class="app-item-logo" src="@/assets/images/logo.png" alt="logo" />
          <div class="app-item-title" :title="item.title">{{ item.title }}</div>
          <a-tag :color="getAppTypeColor(item.type)" class="app-item-tag">
            <i :class="['iconfont', getAppTypeIcon(item.type)]" />
            <span>{{ getAppTypeName(item.type) }}</span>
          </a-tag>
        </div>
        <div class="app-item-desc">{{ item.desc }}</div>
        <div class="app-item-info">
          <div class="app-item-info-base">
            <div class="info-item" v-for="info in getInfoList(item)" :key="info.icon">
              <SvgIcon :name="info.icon" :iconStyle="svgIconStyle" />
              <span>{{ info.text }}</span>
            </div>
          </div>
          <a-dropdown @click.stop @select="({ key }) => handleApplicationOprea(key, item)">
            <div class="app-item-operation">
              <SvgIcon name="more" :iconStyle="opreateSvgIconStyle" />
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="edit"> <i class="iconfont icon-edit" />编辑</a-menu-item>
                <a-menu-item key="log"> <i class="iconfont icon-log" />运行日志</a-menu-item>
                <a-menu-divider />
                <a-menu-item key="delete" class="operation-delete"> <i class="iconfont icon-delete" />删除 </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-card>
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import SvgIcon from "@/components/SvgIcon/index.vue";

const router = useRouter();
const listRef = ref(null);
const data = ref([
  { id: 1, title: "测试1", type: 1, desc: "描述", ownerUser: "admin", auth: 2, createDate: "2025-02-24" },
  { id: 2, title: "测试2", type: 2, desc: "描述2", ownerUser: "admin2", auth: 1, createDate: "2025-02-24" },
  { id: 3, title: "测试3", type: 3, desc: "描述3", ownerUser: "admin3", auth: 2, createDate: "2025-02-24" },
  { id: 4, title: "测试4", type: 1, desc: "描述4", ownerUser: "admin4", auth: 1, createDate: "2025-02-24" },
  { id: 5, title: "测试5", type: 2, desc: "描述5", ownerUser: "admin5", auth: 2, createDate: "2025-02-24" },
  { id: 6, title: "测试6", type: 3, desc: "描述6", ownerUser: "admin6", auth: 1, createDate: "2025-02-24" }
]);

// 跳转到详情页
const toDetail = ({ id }) => router.push(`/agent/flow/${id}`);

// 获取项目信息列表
const getInfoList = item => [
  { icon: "owner", text: item.ownerUser },
  { icon: item.auth === 1 ? "private" : "collaborate", text: item.auth === 1 ? "私有" : "协作" },
  { icon: "time", text: item.createDate }
];

// 处理应用操作（编辑、删除等）
const handleApplicationOprea = (type, item) =>
  ({
    edit: () => editApplication(item),
    delete: () => deleteApplication(item)
  })[type]?.();

// 编辑应用
const editApplication = item => console.log("编辑", item);

// 删除应用
const deleteApplication = item => console.log("删除", item);

// 应用类型映射
const typeMap = {
  1: { text: "简易配置", color: "blue", iconName: "icon-simpleApp" },
  2: { text: "高级编排", color: "cyan", iconName: "icon-workflow" },
  3: { text: "插件", color: "orange", iconName: "icon-plugin" }
};

// 获取应用图标
const getAppTypeIcon = type => typeMap[type]?.iconName || "";

// 获取应用类型名称
const getAppTypeName = type => typeMap[type]?.text || "";

// 获取应用类型颜色
const getAppTypeColor = type => typeMap[type]?.color || "";

// 图标样式
const svgIconStyle = { width: "14px", height: "14px" };
const opreateSvgIconStyle = { width: "16px", height: "16px" };
</script>

<style scoped lang="scss">
.app-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;

  .app-item {
    cursor: pointer;
    border: 1px solid #d9d9d9;
    border-radius: 10px;
    transition: border-color 0.3s ease;

    &:hover {
      border-color: #1890ff;
    }

    :deep(.ant-card-body) {
      padding: 15px 20px 10px !important;
    }

    .app-item-header {
      display: flex;
      gap: 10px;
      align-items: center;

      .app-item-logo {
        width: 24px;
        height: 24px;
      }

      .app-item-title {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .app-item-tag {
        display: flex;
        align-items: center;
        padding: 4px;
        font-size: 12px;

        .iconfont {
          margin-right: 5px;
          font-size: 14px;
        }
      }
    }

    .app-item-desc {
      display: -webkit-box;
      height: 40px;
      margin-top: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      -webkit-line-clamp: 2;
      font-size: 14px;
      color: rgb(0 0 0 / 65%);
      -webkit-box-orient: vertical;
    }

    .app-item-info {
      display: flex;
      justify-content: space-between;
      height: 24px;
      margin-top: 10px;
      font-size: 12px;
      color: rgb(0 0 0 / 65%);

      .app-item-info-base,
      .app-item-operation {
        display: flex;
        gap: 10px;
        align-items: center;
      }

      .app-item-operation {
        padding: 0 5px;
        cursor: pointer;
        border-radius: 6px;

        &:hover {
          background-color: #e6f7ff;
        }
      }

      .info-item {
        display: flex;
        gap: 3px;
        align-items: center;
      }
    }
  }
}
</style>

<style lang="scss">
.operation-delete {
  color: #ff4d4f !important;
}
</style>
