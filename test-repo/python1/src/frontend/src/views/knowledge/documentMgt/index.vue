<template>
  <div style="padding: 15px">
    <!-- 知识库选择界面 -->
    <div v-if="!knowledgeBaseId && knowledgeBaseList.length > 0" class="kb-selector">
      <a-card :bordered="false" style="max-width: 800px; margin: 40px auto">
        <template #title>
          <div style="text-align: center">
            <h2 style="display: flex; gap: 10px; align-items: center; justify-content: center; margin: 0">
              <FolderOutlined style="color: #667eea" />
              选择知识库
            </h2>
          </div>
        </template>
        <a-spin :spinning="loadingKbList">
          <a-row :gutter="16">
            <a-col :span="8" v-for="kb in knowledgeBaseList" :key="kb.id">
              <div class="kb-card-selector" @click="selectKnowledgeBase(kb)">
                <div class="kb-icon" :style="{ background: kb.color }">
                  {{ kb.icon }}
                </div>
                <div class="kb-name">{{ kb.name }}</div>
                <div class="kb-desc">{{ kb.description || "暂无描述" }}</div>
                <a-tag color="blue">{{ kb.document_count }} 个文档</a-tag>
              </div>
            </a-col>
          </a-row>
        </a-spin>
      </a-card>
    </div>

    <!-- 文档管理界面 -->
    <div v-else-if="knowledgeBaseId">
      <!-- 顶部导航：知识库标题行右侧增加上传按钮 -->
      <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 20px">
        <a-button @click="goBack"> <ArrowLeftOutlined /> 返回知识库 </a-button>
        <div v-if="currentKb" class="header-kb-row">
          <div
            :style="{
              width: '36px',
              height: '36px',
              background: currentKb.color,
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px'
            }"
          >
            {{ currentKb.icon }}
          </div>
          <span style="font-size: 18px; font-weight: 600">{{ currentKb.name }}</span>
          <a-button type="primary" class="header-upload-btn" @click="showUploadModal = true">
            <CloudUploadOutlined /> 上传文档
          </a-button>
        </div>
      </div>

      <!-- 左侧 Tab + 右侧内容 -->
      <a-row :gutter="20">
        <!-- 左侧 Tab 标签 -->
        <a-col :span="4">
          <a-card :bordered="false" class="doc-tabs-card">
            <a-menu v-model:selectedKeys="leftTabKeys" mode="inline" class="left-tabs-menu" :style="{ border: 'none' }">
              <a-menu-item key="overview">
                <FileTextOutlined />
                <span>文档一览</span>
              </a-menu-item>
            </a-menu>
          </a-card>
        </a-col>

        <!-- 右侧：根据 Tab 显示内容 -->
        <a-col :span="20">
          <!-- Tab1: 文档一览（文档列表 + AI 处理流程） -->
          <div v-show="leftTabKeys[0] === 'overview'" class="tab-content">
            <a-row :gutter="20">
              <!-- 左侧：文档列表 -->
              <a-col :span="16">
                <a-row :gutter="20">
                  <!-- 文档列表 -->
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
                            <DatabaseOutlined style="font-size: 16px; color: white" />
                          </div>
                          <span>知识库</span>
                          <a-tag color="purple"> {{ filteredDocuments.length }} / {{ documents.length }} 个文档 </a-tag>
                        </div>
                      </template>
                      <template #extra>
                        <div style="display: flex; align-items: center; gap: 8px">
                          <a-radio-group v-model:value="listViewType" size="small">
                            <a-radio-button value="flat">文件列表</a-radio-button>
                            <a-radio-button value="tree">文件夹</a-radio-button>
                          </a-radio-group>
                          <a-input
                            v-model:value="documentSearchKeyword"
                            allow-clear
                            size="small"
                            placeholder="检索文件名"
                            style="width: 220px"
                          />
                          <a-select
                            v-model:value="documentSortType"
                            :options="documentSortOptions"
                            size="small"
                            style="width: 140px"
                          />
                          <a-button type="text" @click="loadDocuments" size="small">
                            <ReloadOutlined :class="{ 'icon-spin': loadingDocs }" />
                          </a-button>
                        </div>
                      </template>

                      <a-spin :spinning="loadingDocs">
                        <div v-if="displayedDocuments.length === 0" style="padding: 40px 0; text-align: center">
                          <FolderOpenOutlined style="font-size: 40px; color: #d9d9d9" />
                          <p style="margin: 12px 0 0; color: #8c8c8c">
                            {{ documents.length === 0 ? "知识库为空" : "未找到匹配文件" }}
                          </p>
                        </div>

                        <div v-else class="doc-list-scroll">
                          <!-- 平铺列表视图 -->
                          <template v-if="listViewType === 'flat'">
                            <div
                              v-for="item in displayedDocuments"
                              :key="item.id"
                              style="
                                display: flex;
                                gap: 12px;
                                align-items: center;
                                padding: 12px;
                                margin-bottom: 8px;
                                background: #fafafa;
                                border-radius: 8px;
                              "
                            >
                              <FileTextOutlined style="font-size: 20px; color: #667eea" />
                              <div style="flex: 1; min-width: 0">
                                <div style="overflow: hidden; text-overflow: ellipsis; font-weight: 500; white-space: nowrap">
                                  {{ getDisplayFilename(item.filename) }}
                                </div>
                                <div style="margin-top: 2px; font-size: 12px; color: #8c8c8c">
                                  {{ formatFileSize(item.size) }} · {{ formatDate(item.upload_time) }}
                                </div>
                                <div v-if="item.tags && item.tags.length" style="margin-top: 6px">
                                  <a-tag
                                    v-for="tag in item.tags"
                                    :key="tag"
                                    :color="getTagColor(tag)"
                                    size="small"
                                    style="margin-right: 4px"
                                  >
                                    {{ tag }}
                                  </a-tag>
                                </div>
                              </div>
                              <a-tag :color="getParseStatusColor(item.status)" style="margin: 0">
                                {{ getParseStatusText(item) }}
                              </a-tag>
                              <a-button
                                v-if="item.status === 'uploaded'"
                                type="text"
                                size="small"
                                :loading="triggeringParseId === item.id"
                                @click="handleTriggerParse(item)"
                              >
                                开始解析
                              </a-button>
                              <a-button type="text" size="small" @click="handleView(item)">查看</a-button>
                              <a-button type="text" size="small" @click="handleDownload(item)">下载</a-button>
                              <a-popconfirm title="确定删除？" @confirm="handleDelete(item.id)">
                                <a-button type="text" danger size="small">
                                  <DeleteOutlined />
                                </a-button>
                              </a-popconfirm>
                            </div>
                          </template>
                          <!-- 树形文件夹视图 -->
                          <template v-else>
                            <a-tree
                              :tree-data="documentTreeData"
                              :selectable="false"
                              :defaultExpandAll="false"
                              :show-line="true"
                              blockNode
                            >
                              <template #title="{ dataRef }">
                                <div style="display: flex; gap: 12px; align-items: center; width: 100%; padding: 4px 0">
                                  <template v-if="dataRef.isLeaf">
                                    <FileTextOutlined style="font-size: 16px; color: #667eea" />
                                    <div style="flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px">
                                      <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                                        {{ dataRef.title }}
                                      </div>
                                      <div style="font-size: 12px; color: #8c8c8c; white-space: nowrap">
                                        {{ formatFileSize(dataRef.size) }} · {{ formatDate(dataRef.upload_time) }}
                                      </div>
                                      <div v-if="dataRef.tags && dataRef.tags.length" style="display: flex; gap: 4px">
                                        <a-tag v-for="tag in dataRef.tags" :key="tag" :color="getTagColor(tag)" size="small">
                                          {{ tag }}
                                        </a-tag>
                                      </div>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px">
                                      <a-tag :color="getParseStatusColor(dataRef.status)" style="margin: 0">
                                        {{ getParseStatusText(dataRef) }}
                                      </a-tag>
                                      <a-button
                                        v-if="dataRef.status === 'uploaded'"
                                        type="text"
                                        size="small"
                                        :loading="triggeringParseId === dataRef.id"
                                        @click="handleTriggerParse(dataRef)"
                                      >
                                        开始解析
                                      </a-button>
                                      <a-button type="text" size="small" @click="handleView(dataRef)">查看</a-button>
                                      <a-button type="text" size="small" @click="handleDownload(dataRef)">下载</a-button>
                                      <a-popconfirm title="确定删除？" @confirm="handleDelete(dataRef.id)">
                                        <a-button type="text" danger size="small">
                                          <DeleteOutlined />
                                        </a-button>
                                      </a-popconfirm>
                                    </div>
                                  </template>
                                  <template v-else>
                                    <FolderOutlined style="font-size: 16px; color: #faad14" />
                                    <div style="flex: 1; font-weight: 500">
                                      {{ dataRef.title }}
                                    </div>
                                  </template>
                                </div>
                              </template>
                            </a-tree>
                          </template>
                        </div>
                      </a-spin>
                    </a-card>
                  </a-col>
                </a-row>
              </a-col>

              <!-- 右侧：处理流程（仅在上传过程中显示） -->
              <a-col v-show="showProcessFlow" :span="8">
                <a-card :bordered="false" class="card-hover" style="height: 100%">
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
                        <ThunderboltOutlined style="font-size: 16px; color: white" />
                      </div>
                      <span>AI 处理流程</span>
                    </div>
                  </template>

                  <div class="process-container">
                    <!-- 撒花效果 -->
                    <div v-if="showConfetti" class="confetti-container">
                      <div v-for="i in 50" :key="i" class="confetti" :style="getConfettiStyle(i)"></div>
                    </div>

                    <!-- 楼梯轨道 - 从下到上 -->
                    <div class="stairs-track">
                      <div
                        v-for="(step, index) in reversedSteps"
                        :key="index"
                        class="stair-step"
                        :class="{
                          active: currentStep === 4 - index,
                          done: currentStep > 4 - index,
                          waiting: currentStep < 4 - index
                        }"
                        :style="{ '--step-index': index }"
                      >
                        <div class="step-platform">
                          <div class="step-icon">
                            <CheckOutlined v-if="currentStep > 4 - index" />
                            <component v-else :is="step.icon" />
                          </div>
                          <div class="step-info">
                            <div class="step-title">{{ step.title }}</div>
                            <div class="step-desc">
                              {{
                                currentStep === 4 - index ? step.processing : currentStep > 4 - index ? step.done : step.waiting
                              }}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 小机器人 - 从下往上爬 -->
                    <div
                      class="robot-climber"
                      :class="{ climbing: uploading, celebrate: showConfetti }"
                      :style="{ '--current-step': currentStep }"
                    >
                      <div class="robot-body">
                        <div class="robot-antenna"></div>
                        <div class="robot-head">
                          <div class="robot-eye left"></div>
                          <div class="robot-eye right"></div>
                          <div class="robot-mouth" :class="{ happy: showConfetti }"></div>
                        </div>
                        <div class="robot-torso">
                          <div class="robot-screen">
                            <span v-if="showConfetti">🎉</span>
                            <span v-else-if="uploading">{{ uploadProgress }}%</span>
                            <span v-else>AI</span>
                          </div>
                        </div>
                        <div class="robot-arms">
                          <div class="robot-arm left"></div>
                          <div class="robot-arm right"></div>
                        </div>
                        <div class="robot-legs">
                          <div class="robot-leg left"></div>
                          <div class="robot-leg right"></div>
                        </div>
                      </div>
                    </div>

                    <!-- 当前处理文件 -->
                    <div v-if="currentFile" class="current-file fade-in">
                      <FileTextOutlined style="color: #667eea" />
                      <span>{{ decodeFilename(currentFile.name) }}</span>
                    </div>
                  </div>

                  <!-- 底部提示 -->
                  <div
                    style="
                      padding: 16px;
                      margin-top: 20px;
                      background: linear-gradient(135deg, rgb(102 126 234 / 5%), rgb(118 75 162 / 5%));
                      border-radius: 10px;
                    "
                  >
                    <div style="display: flex; gap: 12px">
                      <BulbOutlined style="flex-shrink: 0; margin-top: 2px; font-size: 20px; color: #667eea" />
                      <div style="font-size: 13px; line-height: 1.6; color: #666666">
                        文档将通过 AI 自动解析，提取关键信息并建立向量索引，支持智能检索和问答。
                      </div>
                    </div>
                  </div>
                </a-card>
              </a-col>
            </a-row>
          </div>
        </a-col>
      </a-row>

      <!-- 上传文档弹窗（由顶部上传图标触发） -->
      <a-modal v-model:open="showUploadModal" title="上传文档" :footer="null" width="560px" @cancel="closeUploadModal">
        <div v-if="currentKb" class="upload-modal-body">
          <p class="upload-target">
            上传至：<strong>{{ currentKb.name }}</strong>
          </p>
          <a-upload-dragger
            name="file"
            :multiple="true"
            :before-upload="beforeUpload"
            :accept="uploadAccept"
            :show-upload-list="false"
            class="upload-dragger"
          >
            <p class="ant-upload-drag-icon"><InboxOutlined /></p>
            <p class="ant-upload-text">点击或拖拽文件到此区域</p>
            <p class="ant-upload-hint">支持 PDF/Word/Excel/PPT/TXT/Markdown/常见代码文件（点击选择文件）</p>
          </a-upload-dragger>
          <a-upload
            :directory="true"
            :multiple="true"
            :before-upload="beforeUpload"
            :accept="uploadAccept"
            :show-upload-list="false"
          >
            <a-button type="default" size="small" style="margin-bottom: 8px"> <FolderOpenOutlined /> 选择文件夹 </a-button>
          </a-upload>

          <div v-if="fileList.length > 0" class="upload-file-list">
            <div class="upload-file-list-header">
              <span>待上传 ({{ fileList.length }})</span>
              <a-button type="link" size="small" @click="clearUploadFiles">清空</a-button>
            </div>
            <div v-for="(file, index) in fileList" :key="index" class="upload-file-item">
              <FileTextOutlined class="file-icon" />
              <div class="file-info">
                <div class="file-name">{{ decodeFilename(resolveUploadPath(file)) }}</div>
                <a-select
                  v-model:value="fileTags[resolveUploadPath(file)]"
                  mode="multiple"
                  placeholder="选择标签"
                  size="small"
                  style="width: 100%"
                  :options="tagOptions"
                  @change="val => handleTagChange(resolveUploadPath(file), val)"
                >
                  <template #tagRender="{ label, closable, onClose }">
                    <a-tag :color="getTagColor(label)" :closable="closable" @close="onClose" style="margin-right: 3px">
                      {{ label }}
                    </a-tag>
                  </template>
                </a-select>
              </div>
              <a-button type="text" danger size="small" @click="removeFile(index)">
                <DeleteOutlined />
              </a-button>
            </div>
            <div class="upload-tags-quick">
              <span class="label">快捷添加：</span>
              <a-tag
                v-for="tag in defaultTags"
                :key="tag.value"
                :color="tag.color"
                class="quick-tag"
                @click="addTagToAll(tag.value)"
              >
                <PlusOutlined /> {{ tag.label }}
              </a-tag>
            </div>
            <a-button
              type="primary"
              block
              :loading="uploading"
              :disabled="uploading"
              @click="handleUploadAll"
              style="background: linear-gradient(135deg, #667eea, #764ba2); border: none; margin-top: 12px"
            >
              <RocketOutlined /> 开始上传
            </a-button>
          </div>
        </div>
      </a-modal>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { message } from "ant-design-vue";
import {
  FolderOutlined,
  CloudUploadOutlined,
  InboxOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  RocketOutlined,
  BulbOutlined,
  FolderOpenOutlined,
  CheckOutlined,
  ThunderboltOutlined,
  UploadOutlined,
  SearchOutlined,
  BuildOutlined,
  CloudServerOutlined,
  SmileOutlined,
  PlusOutlined,
  ArrowLeftOutlined
} from "@ant-design/icons-vue";
import {
  uploadFiles,
  deleteDocument,
  triggerParse,
  setFolderAssignments,
  getDocumentViewUrl,
  downloadDocument
} from "@/api/modules/document";
import { getKnowledgeBase, getKnowledgeBases, getKnowledgeBaseDocuments } from "@/api/modules/knowledgeBase";

const route = useRoute();
const router = useRouter();

const fileList = ref([]);
const listViewType = ref("flat");
const uploading = ref(false);
const documents = ref([]);
const documentSearchKeyword = ref("");
const documentSortType = ref("upload_time_desc");
const loadingDocs = ref(false);
const triggeringParseId = ref(null); // 正在触发解析的文档 id
const fileTags = ref({}); // 文件标签映射
const currentKb = ref(null);
const knowledgeBaseId = ref(null);

const currentStep = ref(-1);
const uploadProgress = ref(0);
const currentFile = ref(null);
const showConfetti = ref(false);
const showUploadModal = ref(false);
/** 右侧 AI 处理流程卡片：默认不显示，点击开始上传时显示，上传成功后隐藏 */
const showProcessFlow = ref(false);

// 左侧 Tab
const leftTabKeys = ref(["overview"]);

// 返回知识库列表
const goBack = () => {
  router.push("/knowledge/knowledgeMgt");
};

// 加载知识库信息
const loadKnowledgeBase = async () => {
  const kbId = route.query.kb;
  if (kbId) {
    knowledgeBaseId.value = kbId;
    try {
      const res = await getKnowledgeBase(kbId);
      currentKb.value = res;
    } catch (e) {
      message.error("知识库不存在");
      router.push("/knowledge/knowledgeMgt");
    }
  } else {
    // 如果没有指定知识库，加载知识库列表让用户选择
    await loadKnowledgeBaseList();
  }
};

// 加载知识库列表
const knowledgeBaseList = ref([]);
const loadingKbList = ref(false);
const loadKnowledgeBaseList = async () => {
  loadingKbList.value = true;
  try {
    const res = await getKnowledgeBases();
    knowledgeBaseList.value = res.knowledge_bases || [];
    // 如果只有一个知识库，自动选择
    if (knowledgeBaseList.value.length === 1) {
      selectKnowledgeBase(knowledgeBaseList.value[0]);
    }
  } catch (e) {
    message.error("加载知识库失败");
  } finally {
    loadingKbList.value = false;
  }
};

// 选择知识库
const selectKnowledgeBase = kb => {
  router.push(`/knowledge/documentMgt?kb=${kb.id}`);
};

// 预设标签
const defaultTags = [
  { value: "业务", label: "业务", color: "blue" },
  { value: "开发", label: "开发", color: "green" },
  { value: "学习", label: "学习", color: "orange" },
  { value: "规范", label: "规范", color: "purple" },
  { value: "培训", label: "培训", color: "cyan" },
  { value: "产品", label: "产品", color: "magenta" }
];

const tagOptions = defaultTags.map(t => ({ value: t.value, label: t.label }));

const allowedUploadExtensions = new Set([
  "pdf",
  "doc",
  "docx",
  "wps",
  "odt",
  "rtf",
  "xls",
  "xlsx",
  "xlsm",
  "xlt",
  "xltx",
  "xltm",
  "csv",
  "ppt",
  "pptx",
  "pps",
  "ppsx",
  "pot",
  "potx",
  "txt",
  "md",
  "markdown",
  "log",
  "json",
  "yaml",
  "yml",
  "xml",
  "html",
  "htm",
  "css",
  "scss",
  "less",
  "js",
  "jsx",
  "ts",
  "tsx",
  "vue",
  "py",
  "java",
  "c",
  "cc",
  "cpp",
  "h",
  "hpp",
  "go",
  "rs",
  "php",
  "rb",
  "sh",
  "bat",
  "ps1",
  "sql"
]);

const uploadAccept = computed(() => [...allowedUploadExtensions].map(ext => `.${ext}`).join(","));

const getFileExtension = filename => {
  if (!filename || !String(filename).includes(".")) return "";
  return String(filename).split(".").pop().toLowerCase();
};

const resolveUploadPath = file => file?.webkitRelativePath || file?.originFileObj?.webkitRelativePath || file?.name || "unnamed";

// 获取标签颜色
const getTagColor = tag => {
  const found = defaultTags.find(t => t.value === tag);
  return found ? found.color : "default";
};

// 标签变更
const handleTagChange = (filename, tags) => {
  fileTags.value[filename] = tags;
};

// 给所有文件添加标签
const addTagToAll = tag => {
  fileList.value.forEach(file => {
    const key = resolveUploadPath(file);
    if (!fileTags.value[key]) {
      fileTags.value[key] = [];
    }
    if (!fileTags.value[key].includes(tag)) {
      fileTags.value[key].push(tag);
    }
  });
};

const processSteps = [
  { title: "上传文件", icon: UploadOutlined, waiting: "等待上传", processing: "上传中...", done: "上传完成" },
  { title: "AI 解析", icon: SearchOutlined, waiting: "等待解析", processing: "解析内容...", done: "解析完成" },
  { title: "向量化", icon: BuildOutlined, waiting: "等待处理", processing: "生成索引...", done: "索引完成" },
  { title: "写入知识库", icon: CloudServerOutlined, waiting: "等待入库", processing: "写入中...", done: "入库完成" },
  { title: "处理完成", icon: SmileOutlined, waiting: "等待完成", processing: "即将完成...", done: "全部完成！" }
];

// 反转步骤顺序（从下到上显示）
const reversedSteps = computed(() => [...processSteps].reverse());

const documentSortOptions = [
  { label: "最新上传", value: "upload_time_desc" },
  { label: "最早上传", value: "upload_time_asc" },
  { label: "文件名 A-Z", value: "filename_asc" },
  { label: "文件名 Z-A", value: "filename_desc" },
  { label: "文件最大", value: "size_desc" },
  { label: "文件最小", value: "size_asc" }
];

const filteredDocuments = computed(() => {
  const keyword = documentSearchKeyword.value?.trim().toLowerCase();
  if (!keyword) return documents.value;
  return documents.value.filter(item => {
    const filename = decodeFilename(item?.filename || "");
    return String(filename).toLowerCase().includes(keyword);
  });
});

const displayedDocuments = computed(() => {
  const list = [...filteredDocuments.value];
  const sortType = documentSortType.value;

  if (sortType === "upload_time_asc") {
    return list.sort((a, b) => new Date(a?.upload_time || 0).getTime() - new Date(b?.upload_time || 0).getTime());
  }
  if (sortType === "upload_time_desc") {
    return list.sort((a, b) => new Date(b?.upload_time || 0).getTime() - new Date(a?.upload_time || 0).getTime());
  }
  if (sortType === "filename_asc") {
    return list.sort((a, b) => decodeFilename(a?.filename || "").localeCompare(decodeFilename(b?.filename || ""), "zh-CN"));
  }
  if (sortType === "filename_desc") {
    return list.sort((a, b) => decodeFilename(b?.filename || "").localeCompare(decodeFilename(a?.filename || ""), "zh-CN"));
  }
  if (sortType === "size_asc") {
    return list.sort((a, b) => Number(a?.size || 0) - Number(b?.size || 0));
  }
  if (sortType === "size_desc") {
    return list.sort((a, b) => Number(b?.size || 0) - Number(a?.size || 0));
  }
  return list;
});

const documentTreeData = computed(() => {
  const tree = [];

  for (const doc of displayedDocuments.value) {
    const fullName = String(decodeFilename(doc?.filename || "")).replace(/\\/g, "/");
    const segments = fullName.split("/").filter(Boolean);
    if (segments.length === 0) {
      continue;
    }

    let currentChildren = tree;
    let currentPath = "";

    for (let index = 0; index < segments.length; index += 1) {
      const segment = segments[index];
      currentPath = currentPath ? `${currentPath}/${segment}` : segment;
      const isLeaf = index === segments.length - 1;

      if (isLeaf) {
        currentChildren.push({
          ...doc,
          title: segment,
          key: `doc-${doc.id}`,
          isLeaf: true
        });
        continue;
      }

      let folderNode = currentChildren.find(item => !item.isLeaf && item.key === `folder-${currentPath}`);
      if (!folderNode) {
        folderNode = {
          title: segment,
          key: `folder-${currentPath}`,
          isLeaf: false,
          selectable: false,
          children: []
        };
        currentChildren.push(folderNode);
      }
      currentChildren = folderNode.children;
    }
  }

  return tree;
});

// 撒花样式
const getConfettiStyle = i => {
  const colors = ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe", "#00f2fe", "#43e97b", "#38f9d7", "#ffecd2", "#fcb69f"];
  return {
    left: Math.random() * 100 + "%",
    backgroundColor: colors[i % colors.length],
    animationDelay: Math.random() * 0.5 + "s",
    animationDuration: Math.random() * 1 + 2 + "s"
  };
};

const beforeUpload = file => {
  const ext = getFileExtension(file?.name || "");
  if (!allowedUploadExtensions.has(ext)) {
    message.warning(`暂不支持该文件类型：.${ext || "unknown"}`);
    return false;
  }
  fileList.value.push(file);
  return false;
};

const removeFile = index => {
  const filename = resolveUploadPath(fileList.value[index]);
  delete fileTags.value[filename];
  fileList.value.splice(index, 1);
};

const closeUploadModal = () => {
  showUploadModal.value = false;
  fileList.value = [];
  fileTags.value = {};
};

const clearUploadFiles = () => {
  fileList.value = [];
  fileTags.value = {};
};

const simulateProcess = async file => {
  currentFile.value = file;

  for (let i = 0; i < processSteps.length; i++) {
    currentStep.value = i;
    // 每步时间更长，800-1200ms
    const duration = 800 + Math.random() * 400;
    const startProgress = (i / processSteps.length) * 100;
    const endProgress = ((i + 1) / processSteps.length) * 100;

    await animateProgress(startProgress, endProgress, duration);
  }

  // 最后一步完成后，设置为完成状态
  currentStep.value = processSteps.length;

  // 显示撒花
  showConfetti.value = true;
  await new Promise(r => setTimeout(r, 2000));
  showConfetti.value = false;
};

const animateProgress = (start, end, duration) => {
  return new Promise(resolve => {
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      uploadProgress.value = Math.round(start + (end - start) * progress);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        resolve();
      }
    };
    animate();
  });
};

const handleUploadAll = async () => {
  if (fileList.value.length === 0) return;
  const kbId = knowledgeBaseId.value;
  if (kbId == null || kbId === "") {
    message.warning("请先选择知识库");
    return;
  }
  uploading.value = true;
  currentStep.value = 0;
  uploadProgress.value = 0;
  showProcessFlow.value = true;
  showUploadModal.value = false;
  leftTabKeys.value = ["overview"];

  try {
    const kbIdNum = Number(kbId);
    const kbRootKey = `kb-${kbIdNum}`;
    const newAssignments = {};
    const currentFiles = [...fileList.value];
    if (currentFiles.length > 0) {
      await simulateProcess(currentFiles[0]);
    }

    const tagsByFilename = {};
    currentFiles.forEach(file => {
      const actualName = resolveUploadPath(file);
      tagsByFilename[actualName] = fileTags.value[actualName] || [];
    });

    const res = await uploadFiles(currentFiles, tagsByFilename, kbIdNum);
    const resultItems = res?.results || [];
    for (const item of resultItems) {
      const docId = item?.file_info?.id;
      if (item?.success && docId != null) {
        newAssignments[String(docId)] = kbRootKey;
      }
    }
    if (Object.keys(newAssignments).length > 0) {
      await setFolderAssignments(newAssignments);
    }

    const successCount = Number(res?.success_count || 0);
    const failedCount = Number(res?.failed_count || 0);
    if (failedCount > 0) {
      message.warning(`批量上传完成：成功 ${successCount}，失败 ${failedCount}`);
    } else {
      message.success(`全部文档已成功入库（${successCount}）`);
    }
    fileList.value = [];
    fileTags.value = {};
    showProcessFlow.value = false;
    loadDocuments();
  } catch (error) {
    message.error("上传失败");
  } finally {
    uploading.value = false;
    currentStep.value = -1;
    currentFile.value = null;
    uploadProgress.value = 0;
  }
};

const POLL_INTERVAL_MS = 5000;
/** 最多轮询次数（约 10 分钟），防止回调未更新状态时无限轮询 */
const POLL_MAX_COUNT = 120;
let pollTimerId = null;
let pollCount = 0;

const loadDocuments = async () => {
  if (!knowledgeBaseId.value) return;
  loadingDocs.value = true;
  try {
    const kbId = Number(knowledgeBaseId.value);
    const response = await getKnowledgeBaseDocuments(kbId);
    documents.value = response.documents || [];
    pollCount = 0;
    startOrStopPolling();
  } catch (error) {
    message.error("加载失败");
  } finally {
    loadingDocs.value = false;
  }
};

/** 若有文档处于「解析中」，则每 5 秒刷新列表；全部完成或达到最大次数后停止轮询 */
const startOrStopPolling = () => {
  const hasProcessing = documents.value.some(d => d.status === "processing");
  if (hasProcessing && !pollTimerId) {
    pollTimerId = setInterval(() => {
      if (knowledgeBaseId.value && !loadingDocs.value) {
        pollCount += 1;
        if (pollCount > POLL_MAX_COUNT) {
          if (pollTimerId) clearInterval(pollTimerId);
          pollTimerId = null;
          message.info("解析状态轮询已停止，若文档已解析完成请手动刷新");
          return;
        }
        getKnowledgeBaseDocuments(Number(knowledgeBaseId.value)).then(res => {
          documents.value = res.documents || [];
          if (!documents.value.some(d => d.status === "processing")) {
            if (pollTimerId) clearInterval(pollTimerId);
            pollTimerId = null;
          }
        });
      }
    }, POLL_INTERVAL_MS);
  } else if (!hasProcessing && pollTimerId) {
    clearInterval(pollTimerId);
    pollTimerId = null;
  }
};

const handleDelete = async docId => {
  try {
    await deleteDocument(docId);
    message.success("删除成功");
    loadDocuments();
  } catch (error) {
    message.error("删除失败");
  }
};

const handleView = item => {
  const url = getDocumentViewUrl(item.id);
  window.open(url, "_blank");
};

const handleDownload = async item => {
  try {
    const data = await downloadDocument(item.id);
    const blob = data instanceof Blob ? data : new Blob([data]);
    const objectUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = decodeFilename(item.filename || `document-${item.id}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(objectUrl);
  } catch (error) {
    message.error(error?.response?.data?.msg || error?.message || "下载失败");
  }
};

/** 对「仅入库」文档触发解析并写入 ES */
const handleTriggerParse = async item => {
  if (item.status !== "uploaded") return;
  triggeringParseId.value = item.id;
  try {
    await triggerParse(item.id);
    message.success("已提交解析任务，请稍后刷新查看状态");
    loadDocuments();
  } catch (error) {
    message.error(error?.response?.data?.detail || error?.message || "触发解析失败");
  } finally {
    triggeringParseId.value = null;
  }
};

const formatFileSize = bytes => {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
};

const formatDate = dateStr => new Date(dateStr).toLocaleString("zh-CN");

const decodeFilename = name => {
  if (!name || typeof name !== "string") return name;
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
};

const getDisplayFilename = name => {
  const decoded = String(decodeFilename(name) || "");
  const normalized = decoded.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  return parts.length ? parts[parts.length - 1] : decoded;
};

/** 解析状态文案：pending 待解析，processing 解析中，completed 解析成功，failed 解析失败，uploaded 仅入库未解析 */
const getParseStatusText = item => {
  const status = item?.status || "pending";
  const map = {
    pending: "待解析",
    processing: "解析中",
    completed: "解析成功",
    failed: "解析失败",
    uploaded: "仅入库"
  };
  const text = map[status] || "待解析";
  if (status === "completed" && item?.chunk_count > 0) {
    return `${text}(${item.chunk_count}段)`;
  }
  return text;
};

/** 解析状态标签颜色 */
const getParseStatusColor = status => {
  const map = {
    pending: "default",
    processing: "processing",
    completed: "success",
    failed: "error",
    uploaded: "default"
  };
  return map[status] || "default";
};

onUnmounted(() => {
  if (pollTimerId) {
    clearInterval(pollTimerId);
    pollTimerId = null;
  }
});

// 监听路由 query.kb：从知识库管理点击进入或选择知识库时，加载对应知识库并显示其文档
watch(
  () => route.query.kb,
  async () => {
    await loadKnowledgeBase();
    if (knowledgeBaseId.value) {
      loadDocuments();
    }
  },
  { immediate: true }
);
</script>

<style scoped lang="scss">
@keyframes confetti-fall {
  0% {
    top: -10px;
    opacity: 1;
    transform: translateX(0) rotate(0deg);
  }

  100% {
    top: 100%;
    opacity: 0;
    transform: translateX(100px) rotate(720deg);
  }
}

@keyframes antenna-glow {
  0%,
  100% {
    box-shadow:
      0 0 5px #f093fb,
      0 0 10px #764ba2;
    transform: translateX(-50%) scale(1);
  }

  50% {
    box-shadow:
      0 0 15px #f093fb,
      0 0 25px #764ba2;
    transform: translateX(-50%) scale(1.2);
  }
}

@keyframes eyeLook {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-2px);
  }
}

@keyframes smile {
  0% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.3);
  }

  100% {
    transform: scale(1);
  }
}

@keyframes armSwing {
  0%,
  100% {
    transform: rotate(-15deg);
  }

  50% {
    transform: rotate(15deg);
  }
}

@keyframes armCelebrate {
  0%,
  100% {
    transform: rotate(-45deg);
  }

  50% {
    transform: rotate(45deg);
  }
}

@keyframes legWalk {
  0%,
  100% {
    transform: translateY(0) rotate(0);
  }

  50% {
    transform: translateY(-6px) rotate(10deg);
  }
}

@keyframes legJump {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-8px);
  }
}

/* 动画 */
@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgb(102 126 234 / 40%);
    transform: scale(1);
  }

  50% {
    box-shadow: 0 0 0 8px rgb(102 126 234 / 0%);
    transform: scale(1.05);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

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

.process-container {
  position: relative;
  min-height: 400px;
  padding: 20px 0;
}

/* 撒花容器 */
.confetti-container {
  position: absolute;
  inset: 0;
  z-index: 100;
  overflow: hidden;
  pointer-events: none;
}

.confetti {
  position: absolute;
  top: -10px;
  width: 10px;
  height: 10px;
  animation: confetti-fall linear forwards;
}

.confetti:nth-child(odd) {
  border-radius: 50%;
}

.confetti:nth-child(even) {
  border-radius: 2px;
  transform: rotate(45deg);
}

/* 楼梯轨道 - 从下到上 */
.stairs-track {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stair-step {
  display: flex;
  padding-left: calc((4 - var(--step-index)) * 15px);
  transition: all 0.3s;
}

.step-platform {
  display: flex;
  flex: 1;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border-left: 3px solid #e0e0e0;
  border-radius: 10px;
  transition: all 0.3s;
}

.stair-step.active .step-platform {
  background: linear-gradient(135deg, rgb(102 126 234 / 15%), rgb(118 75 162 / 15%));
  border-left-color: #667eea;
  box-shadow: 0 4px 15px rgb(102 126 234 / 25%);
}

.stair-step.done .step-platform {
  background: rgb(82 196 26 / 10%);
  border-left-color: #52c41a;
}

.step-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 16px;
  border-radius: 50%;
  transition: all 0.3s;
}

.stair-step.waiting .step-icon {
  color: #bfbfbf;
  background: #f0f0f0;
}

.stair-step.active .step-icon {
  color: white;
  background: linear-gradient(135deg, #667eea, #764ba2);
  animation: pulse 1.5s ease-in-out infinite;
}

.stair-step.done .step-icon {
  color: white;
  background: #52c41a;
}

.step-info {
  flex: 1;
  min-width: 0;
}

.step-title {
  margin-bottom: 2px;
  font-size: 14px;
  font-weight: 500;
}

.stair-step.waiting .step-title {
  color: #bfbfbf;
}

.stair-step.active .step-title {
  color: #667eea;
}

.stair-step.done .step-title {
  color: #52c41a;
}

.step-desc {
  font-size: 12px;
  color: #8c8c8c;
}

/* 小机器人 - 从下往上 */
.robot-climber {
  position: absolute;

  /* 初始在最底部，随着step增加往上爬 */
  bottom: calc(10px + var(--current-step, -1) * 68px);
  left: -8px;
  z-index: 10;
  transition: bottom 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.robot-body {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 44px;
}

.robot-antenna {
  position: relative;
  width: 4px;
  height: 10px;
  background: linear-gradient(180deg, #764ba2, #667eea);
  border-radius: 2px;
}

.robot-antenna::after {
  position: absolute;
  top: -6px;
  left: 50%;
  width: 10px;
  height: 10px;
  content: "";
  background: radial-gradient(circle, #f093fb, #764ba2);
  border-radius: 50%;
  transform: translateX(-50%);
  animation: antenna-glow 1s infinite;
}

.robot-head {
  position: relative;
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 26px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 10px 10px 6px 6px;
  box-shadow: 0 2px 8px rgb(102 126 234 / 30%);
}

.robot-eye {
  position: relative;
  width: 7px;
  height: 7px;
  background: white;
  border-radius: 50%;
}

.robot-eye::after {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 3px;
  height: 3px;
  content: "";
  background: #1a1a2e;
  border-radius: 50%;
}

.robot-climber.climbing .robot-eye {
  animation: eyeLook 0.8s infinite;
}

.robot-mouth {
  position: absolute;
  bottom: 4px;
  width: 8px;
  height: 3px;
  background: #1a1a2e;
  border-radius: 0 0 4px 4px;
}

.robot-mouth.happy {
  width: 12px;
  height: 6px;
  border-radius: 0 0 6px 6px;
  animation: smile 0.5s ease;
}

.robot-torso {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 32px;
  margin-top: 2px;
  background: linear-gradient(180deg, #5a67d8, #667eea);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgb(102 126 234 / 20%);
}

.robot-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 18px;
  font-family: monospace;
  font-size: 11px;
  font-weight: bold;
  color: #00ff88;
  background: #1a1a2e;
  border-radius: 4px;
  box-shadow: inset 0 0 5px rgb(0 255 136 / 30%);
}

.robot-arms {
  position: absolute;
  top: 40px;
  display: flex;
  justify-content: space-between;
  width: 56px;
}

.robot-arm {
  width: 8px;
  height: 20px;
  background: linear-gradient(180deg, #667eea, #5a67d8);
  border-radius: 4px;
}

.robot-climber.climbing .robot-arm.left {
  transform-origin: top center;
  animation: armSwing 0.4s infinite;
}

.robot-climber.climbing .robot-arm.right {
  transform-origin: top center;
  animation: armSwing 0.4s infinite reverse;
}

.robot-climber.celebrate .robot-arm {
  animation: armCelebrate 0.3s infinite !important;
}

.robot-legs {
  display: flex;
  gap: 10px;
  margin-top: 2px;
}

.robot-leg {
  width: 10px;
  height: 14px;
  background: linear-gradient(180deg, #4c51bf, #434190);
  border-radius: 0 0 4px 4px;
}

.robot-climber.climbing .robot-leg.left {
  animation: legWalk 0.3s infinite;
}

.robot-climber.climbing .robot-leg.right {
  animation: legWalk 0.3s infinite 0.15s;
}

.robot-climber.celebrate .robot-leg {
  animation: legJump 0.2s infinite !important;
}

/* 当前文件 */
.current-file {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  font-size: 13px;
  color: #666666;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgb(0 0 0 / 10%);
}

.icon-spin {
  animation: spin 1s linear infinite;
}

.fade-in {
  animation: fadeIn 0.3s ease;
}

/* 知识库选择卡片 */
.kb-selector {
  .kb-card-selector {
    padding: 24px;
    margin-bottom: 16px;
    text-align: center;
    cursor: pointer;
    border: 2px solid #f0f0f0;
    border-radius: 12px;
    transition: all 0.3s;

    &:hover {
      border-color: #667eea;
      box-shadow: 0 8px 24px rgb(102 126 234 / 20%);
      transform: translateY(-4px);
    }

    .kb-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 64px;
      height: 64px;
      margin: 0 auto 16px;
      font-size: 32px;
      border-radius: 16px;
    }

    .kb-name {
      margin-bottom: 8px;
      font-size: 16px;
      font-weight: 600;
      color: #262626;
    }

    .kb-desc {
      min-height: 40px;
      margin-bottom: 12px;
      font-size: 13px;
      color: #8c8c8c;
    }
  }
}

/* 左侧 Tab */
.doc-tabs-card :deep(.ant-card-body) {
  padding: 8px 0;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.doc-tabs-card :deep(.ant-card-body)::-webkit-scrollbar {
  width: 6px;
}

.doc-tabs-card :deep(.ant-card-body)::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 3px;
}

.doc-tabs-card :deep(.ant-card-body)::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.left-tabs-menu :deep(.ant-menu-item) {
  margin: 4px 8px;
  border-radius: 8px;
}

.tab-content {
  min-height: 400px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  overflow-x: hidden;
}

.tab-settings {
  padding: 0;
}

/* 右侧内容区滚动条 */
.tab-content::-webkit-scrollbar {
  width: 8px;
}

.tab-content::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 4px;
}

.tab-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.tab-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 文档列表滚动 */
.doc-list-scroll {
  max-height: 525px;
  overflow-y: auto;
}

.doc-list-scroll::-webkit-scrollbar {
  width: 6px;
}

.doc-list-scroll::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 3px;
}

.doc-list-scroll::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

/* 文档上传参数设置：Tab 内容可滚动，保存按钮始终可见 */
.config-card {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 200px);
}

.config-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding-bottom: 0;
}

.config-card :deep(.ant-tabs) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.config-card :deep(.ant-tabs-card > .ant-tabs-nav) {
  flex-shrink: 0;
}

.config-card :deep(.ant-tabs-card .ant-tabs-content) {
  margin-top: 0;
  flex: 1;
  min-height: 0;
}

.config-card :deep(.ant-tabs-content-holder) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.config-card :deep(.ant-tabs-content) {
  height: 100%;
  overflow-y: auto;
}

.config-card :deep(.ant-tabs-tabpane) {
  padding-bottom: 8px;
}

/* Tab 内容区滚动条 */
.config-card :deep(.ant-tabs-content)::-webkit-scrollbar {
  width: 8px;
}

.config-card :deep(.ant-tabs-content)::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 4px;
}

.config-card :deep(.ant-tabs-content)::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.config-card :deep(.ant-tabs-content)::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.config-save-bar {
  flex-shrink: 0;
  padding: 16px 0 8px;
  border-top: 1px solid #f0f0f0;
  margin-top: 16px;
  background: #fff;
}

.config-section {
  padding: 16px 0;
  max-height: calc(100vh - 320px);
  overflow-y: auto;

  h3 {
    margin: 0 0 8px;
    font-size: 16px;
  }
}

.config-desc {
  color: #8c8c8c;
  font-size: 13px;
  margin-bottom: 16px;
}

.config-form {
  max-width: 480px;
  margin-top: 16px;
}

.config-form :deep(.ant-form-item) {
  margin-bottom: 12px;
}

.icon-picker-small,
.color-picker-small {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.icon-picker-small .icon-option {
  width: 32px;
  height: 32px;
  font-size: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  cursor: pointer;

  &.active {
    background: rgb(102 126 234 / 10%);
    border-color: #667eea;
  }
}

.color-picker-small .color-option {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;

  &.active {
    border-color: #262626;
  }
}

/* 顶部知识库标题行 + 上传按钮 */
.header-kb-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.header-upload-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 4px;
}

/* 上传弹窗 */
.upload-modal-body {
  padding: 8px 0;
}

.upload-target {
  margin-bottom: 16px;
  font-size: 14px;
  color: #595959;
}

.upload-dragger {
  margin-bottom: 16px;
}

.upload-file-list {
  margin-top: 16px;
}

.upload-file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
}

.upload-file-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 8px;
  margin-bottom: 8px;
}

.upload-file-item .file-icon {
  font-size: 20px;
  color: #667eea;
  flex-shrink: 0;
}

.upload-file-item .file-info {
  flex: 1;
  min-width: 0;
}

.upload-file-item .file-name {
  margin-bottom: 6px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-tags-quick {
  margin: 12px 0;
}

.upload-tags-quick .label {
  margin-right: 8px;
  font-size: 12px;
  color: #8c8c8c;
}

.upload-tags-quick .quick-tag {
  cursor: pointer;
  margin-bottom: 4px;
}
</style>
