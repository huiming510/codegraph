import request from "@/api";

/**
 * @name LLM配置模块
 * 页面：系统 - LLM 配置 (llmConfig/index.vue)
 *
 * 页面功能与接口对应：
 * - 设置默认模型：getDefaultModels、updateDefaultModels、getDefaultModelOptions
 * - 已添加的模型：getAddedProviders
 * - 参数配置（弹窗）：getModelConfig、updateLLMConfig、testLLMConnection
 * - 删除：deleteModelConfig
 * - 可选模型（搜索 + 点击 Tag 筛选）：getOptionalModels({ search?, capability? })
 */

// 默认模型配置
export const getDefaultModels = () => request.get("/llm/default-models");
export const updateDefaultModels = data => request.post("/llm/default-models", data);
export const getDefaultModelOptions = () => request.get("/llm/default-model-options");

// 已添加的模型（按供应商分组，左侧「添加了的模型」）
export const getAddedProviders = () => request.get("/llm/added-providers");

// 可选模型供应商（右侧「可选模型」面板，支持搜索与能力筛选）
// 查询参数直接传第二项，URL 形如 ?search=xxx&capability=MODERATION
export const getOptionalProviders = (params = {}) => request.get("/llm/optional-providers", params);

// 可选模型扁平列表（一行一个模型）
export const getOptionalModels = (params = {}) => request.get("/llm/optional-models", params);

// LLM 供应商树（全部模型 / 公有模型API / 私有模型）
export const getLLMTree = () => request.get("/llm/tree");

// 模型扁平列表：scope=all|shared|private，或 provider=xxx
export const getModelsList = (params = {}) => request.get("/llm/models", params);

// LLM 配置：按模型获取 / 保存 / 删除
export const getLLMProviders = () => request.get("/llm/providers");

export const getModelConfig = (provider, model) => request.get("/llm/config", { provider, model });

export const updateLLMConfig = data => request.post("/llm/config", data);

export const deleteModelConfig = (provider, model) => request.delete("/llm/config", { provider, model });

export const testLLMConnection = data => request.post("/llm/test", data || {});

// 嵌入模型配置
export const getEmbeddingProviders = () => request.get("/embedding/providers");

export const updateEmbeddingConfig = data => request.post("/embedding/config", data);

export const testEmbeddingConnection = () => request.post("/embedding/test");

// 获取当前配置
export const getCurrentConfig = () => request.get("/config/current");
