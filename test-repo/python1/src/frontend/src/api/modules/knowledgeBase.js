import request from "@/api";

/**
 * @name 知识库模块
 */

// 获取知识库列表
export const getKnowledgeBases = (params = {}) => {
  return request.get("/knowledge-bases", params);
};

// 创建知识库
export const createKnowledgeBase = data => {
  return request.post("/knowledge-bases", data);
};

// 获取知识库详情
export const getKnowledgeBase = id => {
  return request.get(`/knowledge-bases/${id}`);
};

// 更新知识库
export const updateKnowledgeBase = (id, data) => {
  return request.put(`/knowledge-bases/${id}`, data);
};

// 删除知识库
export const deleteKnowledgeBase = id => {
  return request.delete(`/knowledge-bases/${id}`);
};

// 获取知识库文档
export const getKnowledgeBaseDocuments = id => {
  return request.get(`/knowledge-bases/${id}/documents`);
};
