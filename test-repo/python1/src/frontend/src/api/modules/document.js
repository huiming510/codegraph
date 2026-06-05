import request from "@/api";

/**
 * @name 文档模块
 */

/**
 * 上传文件到知识库
 * @param {File} file - 文件
 * @param {string[]} tags - 标签
 * @param {number|null} knowledgeBaseId - 知识库 id，必填以关联知识库
 * @param {boolean} skipParse - 为 true 时仅入库不解析（状态 uploaded）
 */
export const uploadFile = (file, tags = [], knowledgeBaseId = null, skipParse = false) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("tags", tags.join(","));
  if (knowledgeBaseId != null && knowledgeBaseId !== "") {
    formData.append("knowledge_base_id", Number(knowledgeBaseId));
  }
  if (skipParse) {
    formData.append("skip_parse", "true");
  }
  return request.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
};

/**
 * 批量上传文件到知识库（单次请求）。
 * @param {File[]} files - 文件列表
 * @param {Record<string, string[]>} tagsByFilename - 每个文件名对应标签
 * @param {number|null} knowledgeBaseId - 知识库 id
 * @param {boolean} skipParse - 为 true 时仅入库不解析
 */
export const uploadFiles = (files = [], tagsByFilename = {}, knowledgeBaseId = null, skipParse = false) => {
  const formData = new FormData();
  const relativePaths = [];

  const getRawFile = file => file?.originFileObj || file;
  const getRelativePath = file =>
    file?.webkitRelativePath || file?.originFileObj?.webkitRelativePath || file?.name || "unnamed";

  (files || []).forEach(file => {
    const relativePath = getRelativePath(file);
    const rawFile = getRawFile(file);
    relativePaths.push(relativePath);
    formData.append("files", rawFile, relativePath);
  });
  formData.append("file_tags_json", JSON.stringify(tagsByFilename || {}));
  formData.append("relative_paths_json", JSON.stringify(relativePaths));
  if (knowledgeBaseId != null && knowledgeBaseId !== "") {
    formData.append("knowledge_base_id", Number(knowledgeBaseId));
  }
  if (skipParse) {
    formData.append("skip_parse", "true");
  }
  return request.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
};

/**
 * 获取文档列表
 * @param {number|null} knowledgeBaseId - 知识库 id，null 表示全部
 * @param {string} search - 文件名模糊检索关键词（仅匹配文件名，不匹配知识库名）
 */
export const getDocuments = (knowledgeBaseId = null, search = "") => {
  const params = {};
  if (knowledgeBaseId != null && knowledgeBaseId !== "") {
    params.knowledge_base_id = Number(knowledgeBaseId);
  }
  if (search && String(search).trim()) {
    params.search = String(search).trim();
  }
  return request.get("/documents", { params });
};

export const deleteDocument = docId => request.delete(`/documents/${docId}`);

/** 文档在线查看地址（用于 window.open） */
export const getDocumentViewUrl = docId => {
  const base = import.meta.env.VITE_APP_API_BASE_URL || "/api";
  return `${base}/documents/${docId}/view`;
};

/** 下载文档（二进制） */
export const downloadDocument = docId => request.get(`/documents/${docId}/download`, {}, { responseType: "blob" });

/** 对「仅入库」的文档触发解析并写入 ES */
export const triggerParse = docId => request.post(`/documents/${docId}/trigger-parse`);

// ==================== 文档管理：虚拟文件夹与归属（后端存储，换机同步） ====================

/** 获取虚拟文件夹列表，knowledge_base_id 为空则全部 */
export const getVirtualFolders = (knowledgeBaseId = null) => {
  const params = knowledgeBaseId != null && knowledgeBaseId !== "" ? { knowledge_base_id: knowledgeBaseId } : {};
  return request.get("/doc-folders/virtual-folders", { params });
};

/** 创建虚拟文件夹 */
export const createVirtualFolder = ({ id, name, parentKey, kbId }) =>
  request.post("/doc-folders/virtual-folders", { id, name, parent_key: parentKey, kb_id: kbId });

/** 删除虚拟文件夹（含子孙），其下文档归属回知识库根 */
export const deleteVirtualFolder = vfId => request.delete(`/doc-folders/virtual-folders/${vfId}`);

/** 获取文档归属 document_id -> parent_key（仅包含在虚拟文件夹内的） */
export const getFolderAssignments = (knowledgeBaseId = null) => {
  const params = knowledgeBaseId != null && knowledgeBaseId !== "" ? { knowledge_base_id: knowledgeBaseId } : {};
  return request.get("/doc-folders/assignments", { params });
};

/** 批量设置文档归属，assignments: { docId: parentKey } */
export const setFolderAssignments = assignments => request.put("/doc-folders/assignments", { assignments });
