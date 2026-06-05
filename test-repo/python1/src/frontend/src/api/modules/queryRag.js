import request from "@/api";

/**
 * @name RAG检索模块
 */

/**
 * RAG 检索接口（流式，后端转发到 QA 服务）
 * @param {string} query 查询内容
 * @param {Object} [options]
 * @param {number} [options.topK]
 * @param {number} [options.knowledgeBaseId]
 * @param {number} [options.searchAppId]
 * @param {string} [options.language] 语言设置，默认 'zh'
 * @param {string} [options.system_prompt] 系统提示词
 * @param {Object} [options.search_options] { top_k, threshold, search_method }
 * @param {Object} [options.generate_options] { model, temperature, top_p }
 * @param {Function} [options.onData] 流式数据回调函数
 * @param {string} [options.token] 用户认证token
 * @returns {Promise} 返回 EventSource 或模拟的流式响应
 */
export const queryRAG = (query, options = {}) => {
  const {
    topK = 20,
    knowledgeBaseId = null,
    searchAppId = null,
    language = 'zh',
    system_prompt = null,
    search_options = null,
    generate_options = null,
    onData = null,
    token = null
  } = options;

  const data = { query };
  if (knowledgeBaseId) data.knowledge_base_id = knowledgeBaseId;
  if (searchAppId) data.search_app_id = searchAppId;
  if (language) data.language = language;
  if (system_prompt) data.system_prompt = system_prompt;
  if (search_options) {
    data.search_options = search_options;
  } else {
    data.top_k = topK;
  }
  if (generate_options) data.generate_options = generate_options;

  // 如果提供了 onData 回调，则使用流式请求
  if (onData) {
    return fetch(`${import.meta.env.VITE_APP_API_BASE_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data)
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      return new Promise((resolve, reject) => {
        let buffer = "";

        const processStream = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split("\n\n");

              // 保留不完整的行
              buffer = lines.pop();

              for (const line of lines) {
                if (line.startsWith("data: ")) {
                  try {
                    const jsonData = JSON.parse(line.slice(6)); // 移除 "data: " 前缀
                    onData(jsonData);
                    if (jsonData.type === "complete" || jsonData.type === "error") {
                      resolve(jsonData);
                      return;
                    }
                  } catch (e) {
                    console.error("解析流式数据失败:", e, line);
                  }
                }
              }
            }

            // 处理剩余的buffer
            if (buffer.trim()) {
              try {
                const jsonData = JSON.parse(buffer.replace("data: ", ""));
                onData(jsonData);
                if (jsonData.type === "complete" || jsonData.type === "error") {
                  resolve(jsonData);
                }
              } catch (e) {
                console.error("解析剩余数据失败:", e, buffer);
              }
            }

            resolve(null);
          } catch (error) {
            reject(error);
          }
        };

        processStream();
      });
    });
  } else {
    // 兼容旧的同步调用（用于测试或回退）
    return request.post("/query", data);
  }
};

/**
 * 获取查询历史记录（直接根据当前用户获取所有历史记录）
 * @returns {Promise} 历史记录数据
 */
export const getQueryHistory = () => {
  return request.get("/history");
};

/**
 * 删除单条查询历史记录
 * @param {number} logId 查询日志ID
 * @returns {Promise} 删除结果
 */
export const deleteQueryLog = (logId) => {
  return request.delete(`/history/${logId}`);
};

/**
 * 清空查询历史记录（清空当前用户的所有历史记录）
 * @returns {Promise} 清空结果
 */
export const clearQueryLogs = () => {
  return request.delete("/history");
};

/**
 * 保存查询结果到数据库
 * @param {Object} queryResult 查询结果数据
 * @param {string} queryResult.query 查询内容
 * @param {string} queryResult.answer AI回答
 * @param {Array} queryResult.sources 相关文档列表
 * @param {number} queryResult.knowledge_base_id 知识库ID
 * @param {number} queryResult.search_app_id 搜索应用ID
 * @param {number} queryResult.top_k 返回文档数量
 * @param {string} [queryResult.llm_id] LLM模型ID
 * @param {number} [queryResult.temperature] 温度参数
 * @param {number} [queryResult.top_p] Top P参数
 * @param {string} [queryResult.search_method] 检索方式
 * @param {number} [queryResult.similarity_threshold] 相似度阈值
 * @returns {Promise} 保存结果
 */
export const saveQueryResult = queryResult => {
  return request.post("/save-query-result", queryResult);
};

/**
 * 获取文档完整内容
 * @param {number} documentId 文档ID
 * @returns {Promise} 文档内容数据
 */
export const getDocumentContent = documentId => {
  return request.get(`/documents/${documentId}/content`);
};
