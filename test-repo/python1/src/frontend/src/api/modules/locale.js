import request from "@/api";

/**
 * 语言切换（与后端 /api/config/locale 对接）
 */

export const getLocaleApi = () => {
  return request.get("/config/locale");
};

export const setLocaleApi = locale => {
  return request.put("/config/locale", { locale });
};
