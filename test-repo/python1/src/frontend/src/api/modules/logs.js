import request from "@/api";

/**
 * @name 日志模块
 */

export const getQueryLogs = (params = {}) => {
  const query = new URLSearchParams();
  if (params.success !== undefined) query.append("success", params.success);
  if (params.skip) query.append("skip", params.skip);
  if (params.limit) query.append("limit", params.limit);
  return request.get(`/logs/query?${query.toString()}`);
};

export const getSystemLogs = (params = {}) => {
  const query = new URLSearchParams();
  if (params.level) query.append("level", params.level);
  if (params.skip) query.append("skip", params.skip);
  if (params.limit) query.append("limit", params.limit);
  return request.get(`/logs/system?${query.toString()}`);
};
