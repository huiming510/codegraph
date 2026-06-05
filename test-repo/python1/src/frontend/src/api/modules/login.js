import request from "@/api";

/**
 * @name 登录模块
 */

// 登录
export const login = params => {
  return request.post("/auth/login", params);
};

// 注册
export const register = params => {
  return request.post("/auth/register", params);
};

// 退出登录
export const logout = () => {
  return request.post("/auth/logout");
};

// 获取当前用户信息
export const getCurrentUser = () => {
  return request.get("/auth/userinfo", {});
};

// 修改密码
export const changePassword = params => {
  return request.put("/auth/password", params);
};

// 获取菜单/路由（由后台按角色返回：admin 全部，普通用户无 system）
export const getMenuList = () => {
  return request.get("/auth/menu");
};
