import request from "@/api";

/**
 * ES 环境配置（解析服务地址、ES 索引名），用于文档解析/trigger-parse
 */
export const getEsConfig = () => request.get("/config/es");

export const updateEsConfig = data => request.put("/config/es", data);
