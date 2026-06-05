<template>
  <div class="all-doc-mgt">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">
          <FolderOutlined class="title-icon" />
          文档管理
        </h2>
        <a-tag color="blue">知识库文件夹大纲</a-tag>
      </div>
    </div>

    <!-- 文档检索：输入即搜，左侧大纲树只显示文件名包含关键词的文档（子串包含，非模糊） -->
    <div v-if="knowledgeBases.length > 0" class="search-bar">
      <span class="search-label">文档检索：</span>
      <a-input
        v-model:value="searchKeyword"
        placeholder="输入关键词，仅显示文件名包含该关键词的文档"
        allow-clear
        class="search-input"
      />
      <span class="search-label">知识库：</span>
      <a-select
        v-model:value="searchKbId"
        placeholder="选择知识库"
        allow-clear
        class="search-kb-select"
        :options="kbSelectOptions"
        :field-names="{ label: 'label', value: 'value' }"
      />
    </div>

    <!-- 无知识库：空状态 -->
    <div v-if="!loading && knowledgeBases.length === 0" class="empty-state">
      <FolderOpenOutlined class="empty-icon" />
      <h3>暂无知识库</h3>
      <p>请先在「知识库」中创建知识库</p>
      <a-button type="primary" @click="goToKnowledgeMgt"> <FolderOutlined /> 前往知识库管理 </a-button>
    </div>

    <!-- 有知识库：左侧大纲树 + 右侧文件一览 -->
    <a-spin :spinning="loading">
      <div v-if="!loading && knowledgeBases.length > 0" class="main-layout">
        <!-- 左侧：大纲树 -->
        <div class="panel-left">
          <div class="panel-title">大纲</div>
          <a-spin :spinning="loadingTree || searchLoading">
            <div v-if="hasNoSearchResults" class="search-empty">未找到文件名包含「{{ searchKeyword }}」的文档</div>
            <div v-else class="tree-wrap">
              <a-tree
                v-model:expandedKeys="expandedKeys"
                v-model:selectedKeys="selectedKeys"
                :tree-data="displayTreeData"
                :load-data="isSearchMode ? undefined : onLoadTreeData"
                :field-names="{ title: 'title', key: 'key', children: 'children' }"
                show-icon
                block-node
                class="outline-tree"
                @select="onTreeSelect"
              >
                <template #icon="{ expanded, dataRef }">
                  <FolderOutlined
                    v-if="dataRef && dataRef.isLeaf === false"
                    :class="expanded ? 'tree-folder-open' : 'tree-folder'"
                  />
                  <FileTextOutlined v-else class="tree-file" />
                </template>
                <template #title="{ title, dataRef }">
                  <span class="tree-node-title" :title="title">{{ title }}</span>
                  <span v-if="dataRef && dataRef.docCount !== undefined && dataRef.isLeaf === false" class="tree-node-count">
                    {{ dataRef.docCount }}
                  </span>
                </template>
              </a-tree>
            </div>
          </a-spin>
        </div>

        <!-- 右侧：文件一览（类 Windows 文件夹） -->
        <div class="panel-right">
          <!-- 所在层级路径（面包屑）+ 操作栏 -->
          <div class="path-bar">
            <a-breadcrumb>
              <a-breadcrumb-item v-for="(crumb, index) in pathCrumbs" :key="crumb.key">
                <a v-if="index < pathCrumbs.length - 1" @click="selectNodeByKey(crumb.key)">{{ crumb.title }}</a>
                <span v-else>{{ crumb.title }}</span>
              </a-breadcrumb-item>
            </a-breadcrumb>
            <div class="path-actions">
              <a-button v-if="selectedKbIdForOps != null" type="primary" size="small" @click="showNewFolderModal = true">
                <FolderOutlined /> 新建文件夹
              </a-button>
              <a-button v-if="selectedKbIdForOps != null" size="small" @click="triggerUpload">
                <UploadOutlined /> 上传文件
              </a-button>
              <a-button
                v-if="selectedKbIdForOps != null"
                size="small"
                :loading="uploadFolderLoading"
                @click="triggerFolderUpload"
              >
                <FolderOutlined /> 上传文件夹
              </a-button>
              <a-popconfirm
                v-if="selectedFileKeys.length > 0"
                title="确定删除所选文件？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleBatchDeleteDocs"
              >
                <a-button type="primary" danger size="small" :loading="batchDeleteLoading">
                  <DeleteOutlined /> 批量删除 ({{ selectedFileKeys.length }})
                </a-button>
              </a-popconfirm>
              <input ref="uploadInputRef" type="file" class="upload-input-hidden" multiple @change="onFileSelected" />
              <input
                ref="folderInputRef"
                type="file"
                class="upload-input-hidden"
                multiple
                webkitdirectory
                directory
                @change="onFolderSelected"
              />
            </div>
          </div>
          <!-- 可滚动视口：列表 + 分页（分页 sticky 常驻底部，列表出现滚动条） -->
          <div class="file-list-viewport">
            <div class="file-list-wrap">
              <a-spin :spinning="loadingTree" class="file-list-spin">
                <div v-if="currentLevelFolders.length === 0 && currentLevelFiles.length === 0" class="file-list-empty">
                  此层级暂无内容
                </div>
                <div v-else class="file-list">
                  <!-- 与左侧知识库文件夹一致的标题行 -->
                  <div class="file-table file-table-header">
                    <span class="col-checkbox">
                      <a-checkbox
                        v-if="currentLevelFiles.length > 0"
                        :checked="isAllFilesSelected"
                        :indeterminate="isSomeFilesSelected"
                        @change="toggleSelectAllFiles"
                      />
                    </span>
                    <span class="col-name">名称</span>
                    <span class="col-size">大小</span>
                    <span class="col-date">上传日期</span>
                    <span class="col-kb">关联知识库</span>
                    <span class="col-action">操作</span>
                  </div>
                  <!-- 文件夹行（与文件表同一列布局） -->
                  <template v-for="item in paginatedItems" :key="item.key">
                    <div
                      v-if="item.isFolder"
                      class="file-table file-table-row folder-row"
                      :class="{ selected: selectedKeys.includes(item.key) }"
                      @click="selectNodeByKey(item.key)"
                      @dblclick="expandAndSelect(item.key)"
                    >
                      <span class="col-checkbox" />
                      <span class="col-name" :title="item.title">
                        <FolderOutlined class="file-icon-inline folder-icon" />
                        {{ item.title }}
                        <span v-if="item.docCount !== undefined" class="file-item-count">{{ item.docCount }}</span>
                      </span>
                      <span class="col-size">{{ item.isVirtual ? "—" : formatFileSize(item.totalSize) || "—" }}</span>
                      <span class="col-date">{{
                        item.isVirtual ? "—" : item.uploadTime ? formatDate(item.uploadTime) : "—"
                      }}</span>
                      <span class="col-kb">—</span>
                      <span class="col-action">
                        <a-button
                          v-if="item.isVirtual"
                          type="link"
                          danger
                          size="small"
                          @click.stop="handleDeleteVirtualFolder(item.key)"
                        >
                          删除
                        </a-button>
                        <span v-else></span>
                      </span>
                    </div>
                    <!-- 文件行：左侧选中文件时高亮 -->
                    <div v-else class="file-table file-table-row file-row" :class="{ selected: selectedFileKey === item.key }">
                      <span class="col-checkbox" @click.stop>
                        <a-checkbox :checked="selectedFileKeys.includes(item.key)" @change="toggleFileSelection(item.key)" />
                      </span>
                      <span class="col-name" :title="item.title">
                        <FileTextOutlined class="file-icon-inline" />
                        {{ item.title }}
                      </span>
                      <span class="col-size">{{ formatFileSize(item.size) }}</span>
                      <span class="col-date">{{ formatDate(item.uploadTime) }}</span>
                      <span class="col-kb">{{ item.kbName || "—" }}</span>
                      <span class="col-action">
                        <a-button type="link" size="small" @click="openFileDetailDrawer(item)"> 查看 </a-button>
                        <a-button
                          v-if="item.status === 'uploaded' || item.status === 'failed'"
                          type="link"
                          size="small"
                          :loading="parseLoadingMap[item.docId]"
                          @click="handleTriggerParse(item)"
                        >
                          解析
                        </a-button>
                        <a-popconfirm
                          title="确定删除该文档？"
                          ok-text="确定"
                          cancel-text="取消"
                          @confirm="handleDeleteDoc(item.docId, item.kbId)"
                        >
                          <a-button type="link" danger size="small">删除</a-button>
                        </a-popconfirm>
                      </span>
                    </div>
                  </template>
                </div>
              </a-spin>
            </div>
            <!-- 分页：sticky 常驻在视口底部，列表多时视口有滚动条 -->
            <div v-if="fileListTotal > 0" class="file-list-pagination">
              <a-pagination
                v-model:current="fileListPage"
                v-model:page-size="fileListPageSize"
                :total="fileListTotal"
                :page-size-options="['10', '20', '50', '100']"
                show-size-changer
                show-quick-jumper
                :show-total="total => `共 ${total} 条`"
              />
            </div>
          </div>
        </div>

        <!-- 新建文件夹弹窗 -->
        <a-modal v-model:open="showNewFolderModal" title="新建文件夹" ok-text="确定" cancel-text="取消" @ok="handleCreateFolder">
          <a-form layout="vertical">
            <a-form-item label="文件夹名称" required>
              <a-input v-model:value="newFolderName" placeholder="请输入文件夹名称" allow-clear />
            </a-form-item>
          </a-form>
        </a-modal>

        <!-- 文件详情抽屉：知识质量评分 + 版本履历 -->
        <a-drawer
          v-model:open="showFileDetailDrawer"
          :title="fileDetailItem ? `${fileDetailItem.title} - 详情` : '文件详情'"
          width="520"
          destroy-on-close
        >
          <template v-if="fileDetailItem">
            <div class="file-detail-section">
              <h4 class="detail-section-title">知识质量评价</h4>
              <div class="quality-score-wrap">
                <span class="quality-score-value">{{ fileQualityScore }}</span>
                <span class="quality-score-unit">分</span>
              </div>
              <p class="quality-score-desc">（当前为演示数据）</p>
            </div>
            <div class="file-detail-section">
              <h4 class="detail-section-title">版本履历</h4>
              <a-table
                :columns="versionColumns"
                :data-source="fileVersionList"
                :pagination="false"
                size="small"
                row-key="version"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'uploadTime'">
                    {{ formatDate(record.uploadTime) }}
                  </template>
                  <template v-else-if="column.key === 'score'"> {{ record.score }} 分 </template>
                  <template v-else-if="column.key === 'download'">
                    <a-button type="link" size="small" @click="handleVersionDownload(record)"> 下载 </a-button>
                  </template>
                </template>
              </a-table>
            </div>
          </template>
        </a-drawer>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import { FolderOutlined, FolderOpenOutlined, FileTextOutlined, UploadOutlined, DeleteOutlined } from "@ant-design/icons-vue";
import { getKnowledgeBases } from "@/api/modules/knowledgeBase";
import {
  getDocuments,
  deleteDocument,
  uploadFile,
  triggerParse,
  getVirtualFolders,
  createVirtualFolder as apiCreateVirtualFolder,
  deleteVirtualFolder as apiDeleteVirtualFolder,
  getFolderAssignments,
  setFolderAssignments
} from "@/api/modules/document";

const router = useRouter();
const knowledgeBases = ref([]);
const loading = ref(false);
const loadingTree = ref(false);
const treeData = ref([]);
const expandedKeys = ref([]);
const selectedKeys = ref(["root"]);
/** 按知识库 id 缓存已加载的文档列表，保证每个节点只显示对应知识库的文件 */
const loadedDocsByKbId = ref({});

/** 虚拟文件夹（后端存储，换机同步），结构：{ id, name, parentKey, kbId }，parentKey 为 kb-{id} 或 vf-{id} */
const virtualFolders = ref([]);
async function loadVirtualFolders() {
  try {
    const res = await getVirtualFolders();
    virtualFolders.value = res.virtual_folders || [];
  } catch (_) {
    virtualFolders.value = [];
  }
}

/** 文档归属路径：docId -> parentKey（后端存储），未设置或为知识库 key 则显示在知识库根下 */
const documentFolderAssignments = ref({});
async function loadDocumentFolderAssignments() {
  try {
    const res = await getFolderAssignments();
    const raw = res.assignments || {};
    documentFolderAssignments.value = typeof raw === "object" ? raw : {};
  } catch (_) {
    documentFolderAssignments.value = {};
  }
}
async function saveDocumentFolderAssignments() {
  try {
    await setFolderAssignments(documentFolderAssignments.value);
    // 保存成功后从服务端重新拉取，保证 key 格式与后端一致（均为字符串）
    await loadDocumentFolderAssignments();
  } catch (err) {
    message.error("保存文档归属失败，文件可能未放入指定目录：" + (err?.message || String(err)));
  }
}

/** 新建文件夹弹窗 */
const showNewFolderModal = ref(false);
const newFolderName = ref("");
const uploadInputRef = ref(null);
const folderInputRef = ref(null);

/** 解析按钮 loading 状态（docId -> boolean） */
const parseLoadingMap = ref({});

/** 右侧文件列表：勾选的文件 key（doc-xxx）列表，切换层级时清空 */
const selectedFileKeys = ref([]);
const isAllFilesSelected = computed(() => {
  const files = currentLevelFiles.value;
  if (!files.length) return false;
  return selectedFileKeys.value.length === files.length;
});
const isSomeFilesSelected = computed(() => {
  const n = selectedFileKeys.value.length;
  return n > 0 && n < currentLevelFiles.value.length;
});
function toggleSelectAllFiles() {
  const files = currentLevelFiles.value;
  if (isAllFilesSelected.value) {
    selectedFileKeys.value = [];
  } else {
    selectedFileKeys.value = files.map(f => f.key);
  }
}
function toggleFileSelection(key) {
  const set = new Set(selectedFileKeys.value);
  if (set.has(key)) set.delete(key);
  else set.add(key);
  selectedFileKeys.value = [...set];
}
const batchDeleteLoading = ref(false);
async function handleBatchDeleteDocs() {
  const toDelete = currentLevelFiles.value.filter(f => selectedFileKeys.value.includes(f.key));
  if (!toDelete.length) return;
  batchDeleteLoading.value = true;
  try {
    for (const item of toDelete) {
      await handleDeleteDoc(item.docId, item.kbId);
    }
    selectedFileKeys.value = [];
    message.success(`已删除 ${toDelete.length} 个文件`);
  } catch (e) {
    message.error("批量删除失败");
  } finally {
    batchDeleteLoading.value = false;
  }
}

/** 文件详情抽屉 */
const showFileDetailDrawer = ref(false);
const fileDetailItem = ref(null);

/** 知识质量评分（假数据）：按 docId 固定一个分数便于演示 */
function getFakeQualityScore(docId) {
  if (docId == null) return 85;
  const n = Number(docId);
  return 72 + (n % 26);
}
const fileQualityScore = computed(() => (fileDetailItem.value ? getFakeQualityScore(fileDetailItem.value.docId) : 0));

/** 版本履历：按「路径key_文件名」存储，localStorage 持久化 */
const VERSION_STORAGE_KEY = "doc_version_history";
function loadVersionHistory() {
  try {
    const raw = localStorage.getItem(VERSION_STORAGE_KEY);
    const data = raw ? JSON.parse(raw) : {};
    return typeof data === "object" ? data : {};
  } catch {
    return {};
  }
}
function saveVersionHistory(data) {
  try {
    localStorage.setItem(VERSION_STORAGE_KEY, JSON.stringify(data));
  } catch (_) {}
}
const versionHistoryStore = ref(loadVersionHistory());

/** 为某路径下某文件追加一条版本记录（上传成功后调用） */
function appendVersionRecord(parentKey, filename, docId) {
  const key = `${parentKey}_${filename}`;
  const store = versionHistoryStore.value;
  const list = Array.isArray(store[key]) ? store[key] : [];
  const score = 70 + Math.floor(Math.random() * 29);
  const next = {
    ...store,
    [key]: [
      ...list,
      {
        version: list.length + 1,
        uploadTime: new Date().toISOString(),
        score,
        docId
      }
    ]
  };
  versionHistoryStore.value = next;
  saveVersionHistory(next);
}

const versionColumns = [
  { title: "上传时间", key: "uploadTime", width: 160 },
  { title: "版本号", dataIndex: "version", key: "version", width: 80 },
  { title: "评分结果", key: "score", width: 90 },
  { title: "操作", key: "download", width: 80 }
];

/** 当前抽屉中文件的版本履历列表（当前路径+文件名） */
const fileVersionList = computed(() => {
  if (!fileDetailItem.value) return [];
  const parentKey = currentViewKey.value;
  const filename = fileDetailItem.value.title;
  const key = `${parentKey}_${filename}`;
  const list = versionHistoryStore.value[key];
  if (!Array.isArray(list) || list.length === 0) {
    return [
      {
        version: 1,
        uploadTime: fileDetailItem.value.uploadTime || new Date().toISOString(),
        score: fileQualityScore.value,
        docId: fileDetailItem.value.docId
      }
    ];
  }
  return [...list];
});

function openFileDetailDrawer(item) {
  fileDetailItem.value = item;
  showFileDetailDrawer.value = true;
}

function handleVersionDownload(record) {
  if (!record?.docId) {
    message.info("下载功能需对接后端接口");
    return;
  }
  const url = `/api/documents/${record.docId}/download`;
  window.open(url, "_blank");
  message.info("已发起下载");
}

/** 文档搜索（仅前端：按文件名包含关键词过滤树，保留层级） */
const searchKeyword = ref("");
const searchKbId = ref(null);
const searchLoading = ref(false);

const isSearchMode = computed(() => !!searchKeyword.value?.trim());

/** 仅选择知识库（未输入关键词）时，大纲只显示该知识库 */
const isKbFilterOnly = computed(() => !isSearchMode.value && searchKbId.value != null && searchKbId.value !== "");

const kbSelectOptions = computed(() => {
  const list = knowledgeBases.value || [];
  return [{ label: "全部知识库", value: null }, ...list.map(kb => ({ label: kb.name, value: kb.id }))];
});

/** 按文件名包含关键词过滤树，保留层级：只保留文件名包含关键词的文档及其祖先节点 */
function filterTreeByFilename(nodes, keyword) {
  if (!nodes || !Array.isArray(nodes)) return [];
  const k = (keyword || "").trim().toLowerCase();
  if (!k) return nodes;
  return nodes
    .map(node => {
      if (node.isLeaf) {
        const title = (node.title ?? "").toLowerCase();
        return title.includes(k) ? { ...node } : null;
      }
      const filteredChildren = filterTreeByFilename(node.children || [], keyword);
      if (filteredChildren.length === 0) return null;
      return { ...node, children: filteredChildren };
    })
    .filter(Boolean);
}

/** 统计树中文档节点（叶子）数量 */
function countDocNodesInTree(nodes) {
  if (!nodes || !Array.isArray(nodes)) return 0;
  return nodes.reduce((sum, node) => {
    if (node.isLeaf) return sum + 1;
    return sum + countDocNodesInTree(node.children || []);
  }, 0);
}

/** 收集树中所有文件夹节点的 key（用于展开） */
function collectFolderKeys(nodes) {
  if (!nodes || !Array.isArray(nodes)) return [];
  const keys = [];
  for (const node of nodes) {
    if (!node.isLeaf) {
      keys.push(node.key);
      keys.push(...collectFolderKeys(node.children || []));
    }
  }
  return keys;
}

/** 显示用树：搜索模式=结合知识库筛选 + 文件名过滤；仅选知识库=只显示该知识库；否则=全部知识库树 */
const displayTreeData = computed(() => {
  if (isSearchMode.value) {
    const keyword = searchKeyword.value?.trim();
    let raw = treeData.value;
    if (!raw?.length) return raw || [];
    const kbId = searchKbId.value;
    if (kbId != null && kbId !== "") {
      const root = raw[0];
      const kbNode = findNodeByKey(raw, `kb-${kbId}`);
      if (!kbNode) {
        return [{ ...root, children: [], title: "全部知识库", key: "root", isLeaf: false, dataRef: { isLeaf: false } }];
      }
      raw = [{ ...root, children: [kbNode], title: "全部知识库", key: "root", isLeaf: false, dataRef: { isLeaf: false } }];
    }
    return filterTreeByFilename(raw, keyword);
  }
  if (isKbFilterOnly.value && searchKbId.value != null) {
    const kbKey = `kb-${searchKbId.value}`;
    const root = treeData.value?.[0];
    if (!root) return treeData.value;
    const kbNode = findNodeByKey(treeData.value, kbKey);
    if (!kbNode) {
      return [{ ...root, children: [], title: "全部知识库", key: "root", isLeaf: false, dataRef: { isLeaf: false } }];
    }
    return [{ ...root, children: [kbNode], title: "全部知识库", key: "root", isLeaf: false, dataRef: { isLeaf: false } }];
  }
  return treeData.value;
});

/** 检索结果树中的文档节点总数（用于判断是否“未找到匹配”） */
const searchResultDocCount = computed(() => {
  if (!isSearchMode.value) return 0;
  return countDocNodesInTree(displayTreeData.value);
});

const hasNoSearchResults = computed(() => isSearchMode.value && !searchLoading.value && searchResultDocCount.value === 0);

// 从树中根据 key 查找节点并返回从根到该节点的路径
function findPathToNode(tree, key, path = []) {
  if (!tree || !Array.isArray(tree)) return null;
  for (const node of tree) {
    const p = [...path, { key: node.key, title: node.title }];
    if (node.key === key) return p;
    if (node.children?.length) {
      const found = findPathToNode(node.children, key, p);
      if (found) return found;
    }
  }
  return null;
}

// 从树中根据 key 查找节点
function findNodeByKey(tree, key) {
  if (!tree || !Array.isArray(tree)) return null;
  for (const node of tree) {
    if (node.key === key) return node;
    if (node.children?.length) {
      const found = findNodeByKey(node.children, key);
      if (found) return found;
    }
  }
  return null;
}

// 从树中查找节点的父节点 key
function findParentKey(tree, key, parentKey = null) {
  if (!tree || !Array.isArray(tree)) return null;
  for (const node of tree) {
    if (node.key === key) return parentKey;
    if (node.children?.length) {
      const found = findParentKey(node.children, key, node.key);
      if (found !== undefined && found !== null) return found;
    }
  }
  return undefined;
}

/** 当前选中的是否为文件节点（doc-xxx） */
const isFileKey = key => typeof key === "string" && key.startsWith("doc-");

/** 右侧面板实际显示的层级 key：选中文件时显示其父文件夹，否则显示选中节点 */
const currentViewKey = computed(() => {
  const key = selectedKeys.value?.[0];
  if (!key) return "root";
  if (isFileKey(key)) {
    const parent = findParentKey(displayTreeData.value, key);
    return parent ?? "root";
  }
  return key;
});

/** 右侧文件列表分页 */
const fileListPage = ref(1);
const fileListPageSize = ref(20);

/** 切换层级时清空文件勾选并重置分页 */
watch(currentViewKey, () => {
  selectedFileKeys.value = [];
  fileListPage.value = 1;
});

/** 左侧选中的文件 key（仅当选中文件时有值），用于右侧高亮并显示该文件详情 */
const selectedFileKey = computed(() => {
  const key = selectedKeys.value?.[0];
  if (!key || !isFileKey(key)) return null;
  return key;
});

/** 当前选中节点路径（面包屑）：以 currentViewKey 为准 */
const pathCrumbs = computed(() => {
  const key = currentViewKey.value;
  if (!key || key === "root") return [{ key: "root", title: "全部知识库" }];
  const path = findPathToNode(displayTreeData.value, key);
  return path?.length ? path : [{ key: "root", title: "全部知识库" }];
});

/** 当前选中对应的知识库 id（用于新建文件夹、上传文件）。以 currentViewKey 为准，选中文件时用其父文件夹 */
const selectedKbIdForOps = computed(() => {
  const key = currentViewKey.value;
  if (!key) return null;
  if (String(key).startsWith("kb-")) {
    const id = Number(String(key).replace(/^kb-/, ""));
    return Number.isNaN(id) ? null : id;
  }
  if (String(key).startsWith("vf-")) {
    const vf = virtualFolders.value.find(f => f.id === String(key).replace(/^vf-/, ""));
    return vf ? vf.kbId : null;
  }
  return null;
});

/** 当前层级：文件夹（知识库节点 + 虚拟文件夹），与右侧表格共用同一标题行 */
const currentLevelFolders = computed(() => {
  const key = currentViewKey.value;
  if (!key) return [];
  const node = findNodeByKey(displayTreeData.value, key);
  const children = node?.children || [];
  return children
    .filter(c => !c.isLeaf)
    .map(c => ({
      key: c.key,
      title: c.title,
      docCount: c.dataRef?.docCount ?? c.docCount,
      isVirtual: !!(c.dataRef?.isVirtual ?? c.isVirtual),
      totalSize: c.dataRef?.totalSize ?? c.totalSize,
      uploadTime: c.dataRef?.uploadTime ?? c.uploadTime ?? c.created_at
    }));
});

/** 当前层级：文件（文档节点），含文件名、大小、上传日期、关联知识库等 */
const currentLevelFiles = computed(() => {
  const key = currentViewKey.value;
  if (!key) return [];
  const node = findNodeByKey(displayTreeData.value, key);
  const children = node?.children || [];
  return children
    .filter(c => c.isLeaf)
    .map(c => ({
      key: c.key,
      title: c.title,
      docId: c.docId,
      kbId: c.kbId,
      size: c.size,
      uploadTime: c.upload_time,
      kbName: c.kbName,
      status: c.status
    }));
});

/** 当前层级合并列表（文件夹在前 + 文件在后），用于分页展示 */
const currentLevelItems = computed(() => {
  const folders = currentLevelFolders.value.map(f => ({ ...f, isFolder: true }));
  const files = currentLevelFiles.value.map(f => ({ ...f, isFolder: false }));
  return [...folders, ...files];
});

/** 分页后的当前页项 */
const paginatedItems = computed(() => {
  const list = currentLevelItems.value;
  const start = (fileListPage.value - 1) * fileListPageSize.value;
  return list.slice(start, start + fileListPageSize.value);
});

/** 右侧文件列表总条数（文件夹+文件） */
const fileListTotal = computed(() => currentLevelItems.value.length);

/** 格式化文件大小 */
const formatFileSize = bytes => {
  if (bytes == null || bytes === 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

/** 格式化上传日期 */
const formatDate = isoStr => {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    return Number.isNaN(d.getTime())
      ? "—"
      : d.toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "—";
  }
};

/** 删除文档后从缓存与路径归属中移除并刷新树 */
const handleDeleteDoc = async (docId, kbId) => {
  try {
    await deleteDocument(docId);
    message.success("删除成功");
    const docs = loadedDocsByKbId.value[kbId];
    if (docs && Array.isArray(docs)) {
      loadedDocsByKbId.value = {
        ...loadedDocsByKbId.value,
        [kbId]: docs.filter(d => d.id !== docId)
      };
    }
    const next = { ...documentFolderAssignments.value };
    delete next[docId];
    documentFolderAssignments.value = next;
    await saveDocumentFolderAssignments();
    buildTreeData();
    if (isSearchMode.value) {
      await onSearch();
    }
  } catch (e) {
    message.error("删除失败");
  }
};

/** 对未解析或解析失败的文档触发解析 */
const handleTriggerParse = async item => {
  if (!item?.docId || !item?.kbId) return;
  parseLoadingMap.value = { ...parseLoadingMap.value, [item.docId]: true };
  try {
    await triggerParse(item.docId);
    message.success("已提交解析任务，请稍后刷新查看状态");
    await reloadKbDocs(item.kbId);
  } catch (e) {
    const msg = e?.response?.data?.detail ?? e?.message ?? "解析触发失败";
    message.error(msg);
  } finally {
    parseLoadingMap.value = { ...parseLoadingMap.value, [item.docId]: false };
  }
};

const onTreeSelect = () => {
  // 选中由 v-model:selectedKeys 同步；若选中知识库节点且未加载文档，则自动加载
  ensureKbDocsLoaded(selectedKeys.value?.[0]);
};
// 若当前选中为知识库节点且未加载过文档，则加载该知识库文档
const ensureKbDocsLoaded = async key => {
  if (!key || !String(key).startsWith("kb-")) return;
  const kbId = Number(String(key).replace(/^kb-/, ""));
  if (Number.isNaN(kbId) || loadedDocsByKbId.value[kbId] !== undefined) return;
  loadingTree.value = true;
  try {
    const res = await getDocuments(kbId);
    let docs = res.documents || [];
    docs = docs.filter(doc => doc.knowledge_base_id === kbId);
    loadedDocsByKbId.value = { ...loadedDocsByKbId.value, [kbId]: docs };
    buildTreeData();
  } catch (e) {
    message.error("加载文档列表失败");
  } finally {
    loadingTree.value = false;
  }
};

/** 强制重新拉取某知识库文档列表并刷新树（用于上传后实时渲染） */
const reloadKbDocs = async kbId => {
  if (kbId == null || Number.isNaN(Number(kbId))) return;
  loadingTree.value = true;
  try {
    const res = await getDocuments(kbId);
    let docs = res.documents || [];
    docs = docs.filter(doc => doc.knowledge_base_id === kbId);
    loadedDocsByKbId.value = { ...loadedDocsByKbId.value, [kbId]: docs };
    buildTreeData();
  } catch (e) {
    message.error("加载文档列表失败");
  } finally {
    loadingTree.value = false;
  }
};
// 点击面包屑或右侧文件夹：选中该节点
const selectNodeByKey = key => {
  selectedKeys.value = [key];
  if (key !== "root" && !expandedKeys.value.includes(key)) {
    expandedKeys.value = [...expandedKeys.value, key];
  }
  ensureKbDocsLoaded(key);
};
// 双击右侧文件夹：展开并选中
const expandAndSelect = key => {
  expandedKeys.value = [...new Set([...expandedKeys.value, key])];
  selectedKeys.value = [key];
  ensureKbDocsLoaded(key);
};

const decodeFilename = name => {
  if (!name || typeof name !== "string") return name;
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
};

// 知识库列表来自接口 knowledge_bases，每项 kb.id 即表 knowledge_bases 的主键 id
const loadKnowledgeBases = async () => {
  loading.value = true;
  try {
    const res = await getKnowledgeBases();
    knowledgeBases.value = res.knowledge_bases || [];
    buildTreeData();
  } catch (e) {
    message.error("加载知识库失败");
  } finally {
    loading.value = false;
  }
};

// 树节点 key = kb-{id}、vf-{id}、doc-{id}；虚拟文件夹注入到知识库节点下
const buildTreeData = () => {
  const list = knowledgeBases.value;
  if (!list.length) {
    treeData.value = [];
    return;
  }
  const loaded = loadedDocsByKbId.value;
  const vfList = virtualFolders.value || [];
  const assignments = documentFolderAssignments.value || {};
  const kbNodes = list.map(kb => {
    const docCount = kb.document_count ?? 0;
    const docs = loaded[kb.id];
    const kbKey = `kb-${kb.id}`;
    const docToNode = doc => ({
      key: `doc-${doc.id}`,
      title: decodeFilename(doc.filename),
      docId: doc.id,
      kbId: kb.id,
      size: doc.size,
      upload_time: doc.upload_time,
      kbName: kb.name,
      status: doc.status,
      isLeaf: true,
      dataRef: { isLeaf: true }
    });
    const buildVfNodes = parentKey =>
      vfList
        .filter(vf => vf.parentKey === parentKey)
        .map(vf => {
          const vfKey = `vf-${vf.id}`;
          const docsInVf = (docs || []).filter(d => (assignments[d.id] || kbKey) === vfKey);
          const vfChildNodes = buildVfNodes(vfKey);
          const directFileCount = docsInVf.length;
          return {
            key: vfKey,
            title: vf.name,
            kbId: vf.kbId,
            isLeaf: false,
            isVirtual: true,
            docCount: directFileCount,
            dataRef: { isLeaf: false, isVirtual: true, docCount: directFileCount },
            children: [...vfChildNodes, ...docsInVf.map(docToNode)]
          };
        });
    const vfNodes = buildVfNodes(kbKey);
    const rootDocs = (docs || []).filter(d => (assignments[d.id] || kbKey) === kbKey);
    const docNodes = rootDocs.map(docToNode);
    const children = [...vfNodes, ...docNodes];
    const totalSize = (docs || []).reduce((s, d) => s + (Number(d.size) || 0), 0);
    const uploadTime = kb.created_at || null;
    return {
      key: kbKey,
      title: kb.name,
      kbId: kb.id,
      docCount,
      isLeaf: false,
      children,
      dataRef: { docCount, isLeaf: false, totalSize, uploadTime }
    };
  });
  treeData.value = [
    {
      key: "root",
      title: "全部知识库",
      children: kbNodes,
      isLeaf: false,
      dataRef: { isLeaf: false }
    }
  ];
  if (!expandedKeys.value.includes("root")) {
    expandedKeys.value = ["root", ...expandedKeys.value];
  }
};

/** 确保参与搜索的知识库文档已加载（选中知识库时只加载该库，否则加载全部；不传 search，由前端按文件名过滤） */
const ensureAllKbsDocsLoaded = async () => {
  const list = knowledgeBases.value || [];
  const loaded = loadedDocsByKbId.value;
  const kbIdFilter = searchKbId.value;
  const toLoad =
    kbIdFilter != null && kbIdFilter !== ""
      ? list.filter(kb => kb.id === kbIdFilter && loaded[kb.id] === undefined)
      : list.filter(kb => loaded[kb.id] === undefined);
  if (toLoad.length === 0) return;
  for (const kb of toLoad) {
    try {
      const res = await getDocuments(kb.id);
      let docs = res.documents || [];
      docs = docs.filter(doc => doc.knowledge_base_id === kb.id);
      loadedDocsByKbId.value = { ...loadedDocsByKbId.value, [kb.id]: docs };
    } catch (e) {
      message.error(`加载知识库「${kb.name}」文档失败`);
    }
  }
  buildTreeData();
};

/** 文档搜索：结合选中的知识库，仅前端按文件名包含关键词过滤树，保留层级；不包含不显示 */
const onSearch = async () => {
  const keyword = searchKeyword.value?.trim();
  if (!keyword) return;
  searchLoading.value = true;
  try {
    await ensureAllKbsDocsLoaded();
    const kbId = searchKbId.value;
    let raw = treeData.value;
    if (kbId != null && kbId !== "" && raw?.length) {
      const root = raw[0];
      const kbNode = findNodeByKey(raw, `kb-${kbId}`);
      raw = kbNode
        ? [{ ...root, children: [kbNode], title: "全部知识库", key: "root", isLeaf: false, dataRef: { isLeaf: false } }]
        : raw;
    }
    const filtered = filterTreeByFilename(raw || [], keyword);
    expandedKeys.value = ["root", ...collectFolderKeys(filtered)];
  } catch (e) {
    message.error("加载文档列表失败");
  } finally {
    searchLoading.value = false;
  }
};

// 展开时：用节点 key 解析出 knowledge_bases.id → 请求 GET /documents?knowledge_base_id=id → 只显示该知识库下的文档
const onLoadTreeData = async treeNode => {
  if (treeNode.key === "root") return Promise.resolve();
  if (!String(treeNode.key || "").startsWith("kb-")) return Promise.resolve();
  const kbId = Number(treeNode.key.replace(/^kb-/, ""));
  if (Number.isNaN(kbId)) return Promise.resolve();
  if (loadedDocsByKbId.value[kbId] !== undefined) return Promise.resolve();

  loadingTree.value = true;
  try {
    const res = await getDocuments(kbId);
    let docs = res.documents || [];
    // 校验：只保留 documents.knowledge_base_id === 当前知识库 id 的文档，与表 knowledge_bases.id 一致
    docs = docs.filter(doc => doc.knowledge_base_id === kbId);
    loadedDocsByKbId.value = { ...loadedDocsByKbId.value, [kbId]: docs };
    buildTreeData();
  } catch (e) {
    message.error("加载文档列表失败");
  } finally {
    loadingTree.value = false;
  }
  return Promise.resolve();
};

const goToKnowledgeMgt = () => {
  router.push("/knowledge/knowledgeMgt");
};

/** 新建文件夹：在当前右侧显示路径（选中的知识库或虚拟文件夹）下创建，后端存储 */
const handleCreateFolder = async () => {
  const name = newFolderName.value?.trim();
  const currentKey = selectedKeys.value?.[0];
  const kbId = selectedKbIdForOps.value;
  if (!name) {
    message.warning("请输入文件夹名称");
    return;
  }
  const isKb = currentKey && String(currentKey).startsWith("kb-");
  const isVf = currentKey && String(currentKey).startsWith("vf-");
  if ((!isKb && !isVf) || kbId == null) {
    message.warning("请先选择知识库或文件夹");
    return;
  }
  const parentKey = currentKey;
  const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  try {
    await apiCreateVirtualFolder({ id, name, parentKey, kbId });
    virtualFolders.value = [...virtualFolders.value, { id, name, parentKey, kbId }];
    buildTreeData();
    if (isVf && !expandedKeys.value.includes(currentKey)) {
      expandedKeys.value = [...expandedKeys.value, currentKey];
    }
    showNewFolderModal.value = false;
    newFolderName.value = "";
    message.success("文件夹已创建");
  } catch (e) {
    message.error("创建文件夹失败");
  }
};

/** 收集虚拟文件夹及其所有子孙的 id（用于级联删除） */
function collectVfIdsToRemove(vfList, parentKey, ids = new Set()) {
  vfList.forEach(f => {
    if (f.parentKey !== parentKey) return;
    ids.add(f.id);
    collectVfIdsToRemove(vfList, `vf-${f.id}`, ids);
  });
  return ids;
}

/** 删除虚拟文件夹（含其下所有子文件夹），并将其下的文档归属回知识库根，后端同步 */
const handleDeleteVirtualFolder = async key => {
  const id = String(key).replace(/^vf-/, "");
  const vf = virtualFolders.value.find(f => f.id === id);
  if (!vf) return;
  const kbId = vf.kbId;
  try {
    await apiDeleteVirtualFolder(id);
    await loadVirtualFolders();
    await loadDocumentFolderAssignments();
    await reloadKbDocs(kbId);
    buildTreeData();
    const toRemove = new Set([id]);
    collectVfIdsToRemove(virtualFolders.value, `vf-${id}`, toRemove);
    const selectedId = selectedKeys.value?.[0]?.replace(/^vf-/, "");
    if (selectedId && toRemove.has(selectedId)) {
      selectedKeys.value = ["root"];
    }
    message.success("已删除");
  } catch (e) {
    message.error("删除文件夹失败");
  }
};

/** 触发文件选择（上传） */
const triggerUpload = () => {
  if (selectedKbIdForOps.value == null) return;
  uploadInputRef.value?.click();
};

/** 触发表单选择文件夹（上传文件夹） */
const triggerFolderUpload = () => {
  if (selectedKbIdForOps.value == null) return;
  folderInputRef.value?.click();
};

/** 根据父节点 key 和文件夹名获取或创建虚拟文件夹（后端存储），返回 vf key */
async function getOrCreateVirtualFolder(parentKey, folderName, kbId) {
  const vfList = virtualFolders.value || [];
  const existing = vfList.find(vf => vf.parentKey === parentKey && vf.name === folderName);
  if (existing) return `vf-${existing.id}`;
  const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  await apiCreateVirtualFolder({ id, name: folderName, parentKey, kbId });
  virtualFolders.value = [...virtualFolders.value, { id, name: folderName, parentKey, kbId }];
  return `vf-${id}`;
}

/** 文件夹选择后：按相对路径创建相同层级虚拟文件夹，并上传所有文件到对应目录 */
const uploadFolderLoading = ref(false);
const onFolderSelected = async e => {
  const fileList = e.target.files;
  const currentKey = selectedKeys.value?.[0];
  const kbId = selectedKbIdForOps.value;
  if (!fileList?.length || kbId == null) {
    e.target.value = "";
    return;
  }
  const isKb = currentKey && String(currentKey).startsWith("kb-");
  const isVf = currentKey && String(currentKey).startsWith("vf-");
  if (!isKb && !isVf) {
    e.target.value = "";
    return;
  }
  const files = Array.from(fileList).filter(f => f.name && !f.name.startsWith("."));
  if (files.length === 0) {
    message.warning("未选择到有效文件");
    e.target.value = "";
    return;
  }
  uploadFolderLoading.value = true;
  try {
    const pathToKey = { "": currentKey };
    const dirPaths = new Set();
    files.forEach(f => {
      const rp = (f.webkitRelativePath || f.name || "").replace(/\\/g, "/");
      const dir = rp.includes("/") ? rp.slice(0, rp.lastIndexOf("/")) : "";
      if (dir) dirPaths.add(dir);
    });
    const sortedDirPaths = Array.from(dirPaths).sort((a, b) => {
      const depthA = (a.match(/\//g) || []).length;
      const depthB = (b.match(/\//g) || []).length;
      return depthA - depthB || a.localeCompare(b);
    });
    for (const dirPath of sortedDirPaths) {
      const parts = dirPath.split("/").filter(Boolean);
      let parentKey = currentKey;
      let acc = "";
      for (const part of parts) {
        acc = acc ? `${acc}/${part}` : part;
        parentKey = await getOrCreateVirtualFolder(parentKey, part, kbId);
        pathToKey[acc] = parentKey;
      }
    }
    let uploaded = 0;
    for (const file of files) {
      const rp = (file.webkitRelativePath || file.name || "").replace(/\\/g, "/");
      const dirPath = rp.includes("/") ? rp.slice(0, rp.lastIndexOf("/")) : "";
      const parentKey = pathToKey[dirPath] || currentKey;
      const res = await uploadFile(file, [], kbId, true);
      const docId = res?.file_info?.id;
      if (docId != null) {
        documentFolderAssignments.value = {
          ...documentFolderAssignments.value,
          [String(docId)]: parentKey
        };
        const fileName = (file.webkitRelativePath || file.name || "").split("/").pop() || file.name;
        appendVersionRecord(parentKey, fileName, docId);
        uploaded += 1;
      }
    }
    if (uploaded > 0) await saveDocumentFolderAssignments();
    message.success(`已上传文件夹：${uploaded} 个文件，目录结构已保留`);
    await reloadKbDocs(kbId);
    buildTreeData();
    const firstDir = sortedDirPaths[0];
    if (firstDir && pathToKey[firstDir]) {
      const key = pathToKey[firstDir];
      if (!expandedKeys.value.includes(key)) {
        expandedKeys.value = [...expandedKeys.value, key];
      }
      selectedKeys.value = [key];
    }
  } catch (err) {
    message.error("上传文件夹失败");
  } finally {
    uploadFolderLoading.value = false;
    e.target.value = "";
  }
};

/** 文件选择后上传到当前右侧路径（知识库或虚拟文件夹） */
const uploadLoading = ref(false);
const onFileSelected = async e => {
  const files = e.target.files;
  const currentKey = selectedKeys.value?.[0];
  const kbId = selectedKbIdForOps.value;
  if (!files?.length || kbId == null) {
    e.target.value = "";
    return;
  }
  const isKb = currentKey && String(currentKey).startsWith("kb-");
  const isVf = currentKey && String(currentKey).startsWith("vf-");
  if (!isKb && !isVf) {
    e.target.value = "";
    return;
  }
  uploadLoading.value = true;
  try {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const res = await uploadFile(file, [], kbId, true);
      const docId = res?.file_info?.id;
      if (docId != null) {
        documentFolderAssignments.value = {
          ...documentFolderAssignments.value,
          [String(docId)]: currentKey
        };
        appendVersionRecord(currentKey, file.name, docId);
      }
    }
    if (files.length > 0) await saveDocumentFolderAssignments();
    message.success(`已上传 ${files.length} 个文件`);
    await reloadKbDocs(kbId);
  } catch (err) {
    message.error("上传失败");
  } finally {
    uploadLoading.value = false;
    e.target.value = "";
  }
};

// 输入即搜：根据文件名关键词，左侧大纲树展开并只显示匹配的文档（无检索按钮）
let searchKeywordTimer = null;
watch(
  searchKeyword,
  () => {
    if (searchKeywordTimer) clearTimeout(searchKeywordTimer);
    searchKeywordTimer = setTimeout(() => {
      onSearch();
      searchKeywordTimer = null;
    }, 300);
  },
  { immediate: false }
);

// 仅选知识库时：加载该知识库文档并选中该节点，使左侧大纲只显示该库；清空时恢复全部
watch(
  searchKbId,
  async kbId => {
    if (searchKeyword.value?.trim()) return; // 有关键词时由搜索逻辑处理
    if (kbId == null || kbId === "") {
      selectedKeys.value = ["root"];
      return;
    }
    const key = `kb-${kbId}`;
    await ensureKbDocsLoaded(key);
    selectedKeys.value = [key];
    if (!expandedKeys.value.includes(key)) {
      expandedKeys.value = ["root", key, ...expandedKeys.value.filter(k => k !== "root")];
    }
  },
  { immediate: false }
);

onMounted(async () => {
  // 清空文档缓存，确保从知识库页面上传的文件在展开知识库时能同步显示
  loadedDocsByKbId.value = {};
  await loadVirtualFolders();
  await loadDocumentFolderAssignments();
  await loadKnowledgeBases();
});
</script>

<style scoped lang="scss">
.all-doc-mgt {
  padding: 16px 24px;
}

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  .search-label {
    font-size: 14px;
    color: #595959;
    flex-shrink: 0;
  }
  .search-input {
    width: 280px;
    min-width: 200px;
  }
  .search-kb-select {
    width: 180px;
    min-width: 140px;
  }
}

.page-header {
  margin-bottom: 20px;
  .header-left {
    display: flex;
    gap: 12px;
    align-items: center;
  }
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  .title-icon {
    color: #667eea;
  }
}

.empty-state {
  padding: 80px 20px;
  text-align: center;
  color: #8c8c8c;
  .empty-icon {
    font-size: 64px;
    color: #d9d9d9;
  }
  h3 {
    margin: 20px 0 8px;
    color: #262626;
    font-size: 18px;
  }
  p {
    margin-bottom: 24px;
    color: #8c8c8c;
  }
}

.main-layout {
  display: flex;
  gap: 0;
  height: calc(100vh - 220px);
  max-height: calc(100vh - 220px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #f0f0f0;
}

.panel-left {
  width: 280px;
  min-width: 280px;
  min-height: 0;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  .panel-title {
    flex-shrink: 0;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 14px;
    color: #262626;
    border-bottom: 1px solid #f0f0f0;
    background: #fff;
  }
  :deep(.ant-spin-nested-loading) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  :deep(.ant-spin-container) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
}

.panel-right {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
}

.path-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 20px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  :deep(.ant-breadcrumb) {
    font-size: 13px;
  }
  :deep(.ant-breadcrumb a) {
    color: #667eea;
  }
  :deep(.ant-breadcrumb a:hover) {
    color: #764ba2;
  }
  .path-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

.upload-input-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.file-table-row.folder-row {
  cursor: pointer;
  &:hover {
    background: #f5f5f5;
  }
  &.selected {
    background: rgba(102, 126, 234, 0.1);
  }
  .file-item-count {
    margin-left: 8px;
    font-size: 12px;
    color: #667eea;
    background: rgba(102, 126, 234, 0.12);
    padding: 2px 8px;
    border-radius: 4px;
  }
}

/* 右侧列表+分页的滚动视口：有滚动条，分页 sticky 在底部 */
.file-list-viewport {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.file-list-wrap {
  padding: 12px 20px 0;
}

.file-list-spin {
  display: block;
  :deep(.ant-spin-nested-loading),
  :deep(.ant-spin-container) {
    display: block;
  }
}

.file-list-wrap .file-list-empty {
  padding: 12px 0 40px;
}

.file-list-wrap .file-list {
  padding: 0 0 16px;
}

/* 分页常驻在视口底部：sticky，列表滚动时分页始终贴底 */
.file-list-pagination {
  position: sticky;
  bottom: 0;
  padding: 12px 20px 16px;
  border-top: 1px solid #f0f0f0;
  background: #fff;
  display: flex;
  justify-content: flex-end;
  z-index: 1;
}

.file-list-empty {
  padding: 40px 16px;
  text-align: center;
  color: #8c8c8c;
  font-size: 14px;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: default;
  transition: background 0.2s;
  .file-item-icon {
    font-size: 18px;
    flex-shrink: 0;
  }
  .file-item-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
  }
  .file-item-count {
    flex-shrink: 0;
    font-size: 12px;
    color: #667eea;
    background: rgba(102, 126, 234, 0.12);
    padding: 2px 8px;
    border-radius: 4px;
  }
}

.folder-item {
  cursor: pointer;
  &:hover {
    background: #f5f5f5;
  }
  &.selected {
    background: rgba(102, 126, 234, 0.1);
  }
}

.folder-icon {
  color: #667eea;
}

.file-icon {
  color: #8c8c8c;
}

.file-item-doc {
  cursor: default;
}

/* 文件表格：表头 + 数据行 */
.file-table {
  display: grid;
  grid-template-columns: 40px minmax(120px, 600px) 100px 160px 140px 80px;
  gap: 12px 16px;
  align-items: center;
  padding: 10px 12px;
  font-size: 14px;
}

.file-table .col-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-table-header {
  color: #8c8c8c;
  font-weight: 500;
  border-bottom: 1px solid #f0f0f0;
  margin-top: 8px;
  padding-bottom: 10px;
}

.file-table-row {
  border-radius: 6px;
  transition: background 0.2s;
  &:hover {
    background: #fafafa;
  }
}

.file-table .col-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon-inline {
  color: #8c8c8c;
  flex-shrink: 0;
}

/* 右侧列表：文件夹图标着色，与文件图标区分 */
.file-table .col-name .folder-icon {
  color: #667eea;
}

.file-table .col-size,
.file-table .col-date {
  color: #595959;
  flex-shrink: 0;
}

.file-table .col-kb {
  color: #595959;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-table .col-action {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 4px;
}

.search-empty {
  padding: 24px 16px;
  text-align: center;
  color: #8c8c8c;
  font-size: 14px;
}

.tree-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 0;
  -webkit-overflow-scrolling: touch;
}

.outline-tree {
  :deep(.ant-tree-treenode) {
    align-items: center;
  }
  :deep(.ant-tree-node-content-wrapper) {
    width: 100%;
  }
  :deep(.ant-tree-title) {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
}

.tree-node-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.tree-node-count {
  flex-shrink: 0;
  padding: 0 6px;
  font-size: 12px;
  line-height: 18px;
  color: #667eea;
  background: rgba(102, 126, 234, 0.12);
  border-radius: 4px;
}

.tree-folder {
  color: #667eea;
}
.tree-folder-open {
  color: #764ba2;
}
.tree-file {
  color: #8c8c8c;
}

/* 文件行：左侧选中文件时高亮 */
.file-table-row.file-row.selected {
  background: rgba(102, 126, 234, 0.1);
}

/* 文件详情抽屉 */
.file-detail-section {
  margin-bottom: 24px;
}
.detail-section-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
}
.quality-score-wrap {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.quality-score-value {
  font-size: 32px;
  font-weight: 600;
  color: #667eea;
}
.quality-score-unit {
  font-size: 16px;
  color: #595959;
}
.quality-score-desc {
  margin: 8px 0 0;
  font-size: 12px;
  color: #8c8c8c;
}
</style>
