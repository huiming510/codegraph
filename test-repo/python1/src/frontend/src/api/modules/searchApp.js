import http from "@/api";

/**
 * 搜索应用相关 API
 */

// 创建搜索应用
export const createSearchApp = data => {
  return http.post("/search-apps", data);
};

// 获取搜索应用列表
export const getSearchApps = () => {
  return http.get("/search-apps");
};

// 更新搜索应用
export const updateSearchApp = (id, data) => {
  return http.put(`/search-apps/${id}`, data);
};

// 删除搜索应用
export const deleteSearchApp = id => {
  return http.delete(`/search-apps/${id}`);
};

// 获取搜索应用详情
export const getSearchAppDetail = id => {
  return http.get(`/search-apps/${id}`);
};
