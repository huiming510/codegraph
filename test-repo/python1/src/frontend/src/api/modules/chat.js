import request from "@/api";
import { useUserStore } from "@/stores/modules/user";

/**
 * 对话模块：流式对话通过后端 /api/chat/stream-external 代理，历史/会话调用 /api/chat
 */

/**
 * 流式对话（通过后端代理调用外部多轮对话 API）
 * @param {Object} params
 * @param {string} params.sessionId - 会话 ID
 * @param {string} params.utterance - 用户输入
 * @param {string} params.index - ES 索引名，如 linkrag_kb_1
 * @param {string} [params.appSessionKey] - 助手 session key，用于会话不存在时创建并关联
 * @param {string} [params.systemPrompt] - 角色/system 提示词（对应助手配置中的「角色」），作为 system_prompt 传给后端
 * @param {Object} [params.searchOptions] - { top_k, threshold, search_method }
 * @param {Object} [params.generateOptions] - { model, temperature, top_p }
 * @param {function(string): void} onChunk - 每收到一块文本时回调
 * @param {function(Array): void} [onReferences] - 收到 event:references 时回调，参数为参照文档数组
 * @param {function(): void} [onDone] - 流结束时回调
 * @returns {Promise<void>}
 */
export async function sendChatStream(
  { sessionId, utterance, index, appSessionKey, systemPrompt, searchOptions = {}, generateOptions = {} },
  { onChunk, onReferences, onDone }
) {
  const base = (import.meta.env.VITE_APP_API_BASE_URL || "/api").replace(/\/$/, "");
  const baseUrl = `${base}/chat/stream-external`;
  const userStore = useUserStore();
  const headers = {
    "Content-Type": "application/json",
    Accept: "text/event-stream"
  };
  if (userStore.token) {
    headers["Authorization"] = `Bearer ${userStore.token}`;
  }
  const body = {
    session_id: sessionId,
    utterance,
    index,
    app_session_key: appSessionKey || undefined,
    system_prompt: systemPrompt || undefined,
    search_options: searchOptions,
    generate_options: generateOptions
  };
  const res = await fetch(baseUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err || `HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") continue;
          if (currentEvent === "delta" && onChunk) {
            onChunk(data);
          } else if (currentEvent === "references" && onReferences) {
            try {
              const refs = JSON.parse(data);
              onReferences(Array.isArray(refs) ? refs : []);
            } catch {
              onReferences([]);
            }
          }
        }
      }
    }
    if (buffer.startsWith("data: ")) {
      const data = buffer.slice(6);
      if (data !== "[DONE]" && currentEvent === "delta" && onChunk) onChunk(data);
    }
  } finally {
    onDone?.();
  }
}

/**
 * 发送对话消息（非流式，调用后端 /api/chat）
 * @param {string} message - 用户输入
 * @param {string|null} sessionId - 会话 ID
 * @param {number|null} knowledgeBaseId - 知识库 ID，可选
 * @returns {Promise<{ response: string, session_id: string }>}
 */
export const sendChatMessage = (message, sessionId = null, knowledgeBaseId = null) => {
  const data = { message, session_id: sessionId };
  if (knowledgeBaseId) {
    data.knowledge_base_id = knowledgeBaseId;
  }
  return request.post("/chat", data);
};

/**
 * 获取会话历史
 * @param {string} sessionId - 会话 ID
 * @returns {Promise<{ messages: Array<{ role, content, timestamp }> }>}
 */
export const getChatHistory = sessionId => {
  return request.get(`/chat/history/${sessionId}`);
};

/**
 * 获取用户会话列表
 * @returns {Promise<{ sessions: Array<{ key, title, message_count, updated_at }> }>}
 */
export const getChatSessions = () => {
  return request.get("/chat/sessions");
};

/**
 * 更新会话/对话标题（首条消息后更新）
 * @param {string} sessionKey - 会话 key（conv_ 或 app_）
 * @param {string} title - 新标题
 */
export const updateSessionTitle = (sessionKey, title) => {
  return request.put(`/chat/sessions/${sessionKey}`, { title });
};
