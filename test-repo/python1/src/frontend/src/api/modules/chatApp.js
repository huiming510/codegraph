import request from "@/api";

/**
 * 聊天应用相关 API
 */

// 创建聊天应用
export const createChatApp = data => {
  return request.post("/chat-apps", data);
};

// 获取聊天应用列表
export const getChatApps = () => {
  return request.get("/chat-apps");
};

// 更新聊天应用
export const updateChatApp = (sessionKey, data) => {
  return request.put(`/chat-apps/${sessionKey}`, data);
};

// 删除聊天应用
export const deleteChatApp = sessionKey => {
  return request.delete(`/chat-apps/${sessionKey}`);
};

// 获取聊天应用详情
export const getChatAppDetail = sessionKey => {
  return request.get(`/chat-apps/${sessionKey}`);
};

/**
 * 更新对话配置（description、search_options、generate_options）到数据库
 * @param {string} sessionKey - 助手 session key（app_ 开头）
 * @param {Object} data - { description?, search_options?, generate_options? }
 */
export const updateChatAppConfig = (sessionKey, data) => {
  return request.put(`/chat-apps/${sessionKey}/config`, data);
};

/**
 * 获取某助手下所有对话列表
 * @param {string} appSessionKey - 助手 session key（app_ 开头）
 * @returns {Promise<{ conversations: Array<{ session_key, title, updated_at }> }>}
 */
export const getAppConversations = appSessionKey => {
  return request.get(`/chat-apps/${appSessionKey}/conversations`);
};

/**
 * 在助手下新建对话（配置继承自助手）
 * @param {string} appSessionKey - 助手 session key（app_ 开头）
 * @returns {Promise<{ session_key, title }>}
 */
export const createAppConversation = appSessionKey => {
  return request.post(`/chat-apps/${appSessionKey}/conversations`);
};

/**
 * 删除助手或对话
 * @param {string} sessionKey - 助手 app_ 或对话 conv_ 的 session key
 */
export const deleteChatSession = sessionKey => {
  return request.delete(`/chat-apps/${sessionKey}`);
};
