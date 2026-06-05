import request from "@/api";

/**
 * @name 用户管理模块
 */

// 获取用户列表
export const getUserListApi = params => {
  return request.get("/users", params);
};

// 创建用户
export const createUserApi = params => {
  return request.post("/users", params);
};

// 更新用户
export const updateUserApi = (userId, params) => {
  return request.put(`/users/${userId}`, params);
};

// 删除用户
export const deleteUserApi = userId => {
  return request.delete(`/users/${userId}`);
};

/**
 * 管理员重置用户密码，对应后端 PUT /api/users/{user_id}/password
 * @param {number} userId - 用户 ID
 * @param {string} password - 新密码（如 123456）
 */
export const resetPasswordApi = (userId, password) => {
  return request.put(`/users/${userId}/password`, { password });
};
