/**
 * 登录/认证 API 模块测试（mock request）
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn()
  }
}));

describe("login API module", () => {
  beforeEach(async () => {
    vi.resetModules();
  });

  it("login 调用 request.post /auth/login 并传入参数", async () => {
    const request = (await import("@/api")).default;
    const { login } = await import("@/api/modules/login.js");
    request.post.mockResolvedValue({ access_token: "xxx", user: { id: 1, username: "admin" } });
    const res = await login({ username: "admin", password: "123" });
    expect(request.post).toHaveBeenCalledWith("/auth/login", { username: "admin", password: "123" });
    expect(res).toHaveProperty("access_token");
  });

  it("login 调用失败时返回 rejected Promise", async () => {
    const request = (await import("@/api")).default;
    const { login } = await import("@/api/modules/login.js");
    request.post.mockRejectedValue(new Error("网络错误"));
    await expect(login({ username: "a", password: "b" })).rejects.toThrow("网络错误");
  });

  it("register 调用 request.post /auth/register 并传入完整参数", async () => {
    const request = (await import("@/api")).default;
    const { register } = await import("@/api/modules/login.js");
    request.post.mockResolvedValue({ success: true });
    await register({ username: "u", password: "p", nickname: "n", email: "e@x.com" });
    expect(request.post).toHaveBeenCalledWith("/auth/register", {
      username: "u",
      password: "p",
      nickname: "n",
      email: "e@x.com"
    });
  });

  it("logout 调用 request.post /auth/logout 无参数", async () => {
    const request = (await import("@/api")).default;
    const { logout } = await import("@/api/modules/login.js");
    request.post.mockResolvedValue({});
    await logout();
    expect(request.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("getCurrentUser 调用 request.get /auth/userinfo", async () => {
    const request = (await import("@/api")).default;
    const { getCurrentUser } = await import("@/api/modules/login.js");
    request.get.mockResolvedValue({ id: 1, username: "admin", role: "admin" });
    const res = await getCurrentUser();
    expect(request.get).toHaveBeenCalledWith("/auth/userinfo", {});
    expect(res.role).toBe("admin");
  });

  it("changePassword 调用 request.put /auth/password 并传入修改密码参数", async () => {
    const request = (await import("@/api")).default;
    const { changePassword } = await import("@/api/modules/login.js");
    request.put.mockResolvedValue({ success: true });
    await changePassword({ old_password: "old", new_password: "new" });
    expect(request.put).toHaveBeenCalledWith("/auth/password", {
      old_password: "old",
      new_password: "new"
    });
  });

  it("getMenuList 调用 request.get /auth/menu 返回菜单数组", async () => {
    const request = (await import("@/api")).default;
    const { getMenuList } = await import("@/api/modules/login.js");
    const menu = [{ path: "/chat", name: "chat", meta: { title: "对话" } }];
    request.get.mockResolvedValue(menu);
    const res = await getMenuList();
    expect(request.get).toHaveBeenCalledWith("/auth/menu");
    expect(res).toEqual(menu);
    expect(res).toHaveLength(1);
  });
});
