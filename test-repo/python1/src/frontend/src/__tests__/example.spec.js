/**
 * 前端单元测试：路由常量、getMenuTitle、checkResStatus、组件
 * 运行：npm run test 或 npm run test:run
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";

describe("路由常量", () => {
  it("登录与首页 URL 正确", async () => {
    const mod = await import("@/constants/router.js");
    expect(mod.HOEM_URL).toBe("/chat");
    expect(mod.LOGIN_URL).toBe("/login");
  });

  it("路由白名单包含 500 错误页", async () => {
    const mod = await import("@/constants/router.js");
    expect(mod.ROUTER_WHITE_LIST).toContain("/500");
  });

  it("菜单 path 兜底名称覆盖主要页面", async () => {
    const mod = await import("@/constants/router.js");
    expect(mod.MENU_PATH_TITLE_MAP["/chat/list"]).toBe("AI 对话");
    expect(mod.MENU_PATH_TITLE_MAP["/query/rag"]).toBe("智能检索");
    expect(mod.MENU_PATH_TITLE_MAP["/knowledge/knowledgeMgt"]).toBe("知识库管理");
  });

  it("MENU_CHILDREN_FALLBACK 包含 chat、knowledge、query 子菜单", async () => {
    const mod = await import("@/constants/router.js");
    expect(mod.MENU_CHILDREN_FALLBACK["/chat"]).toHaveLength(1);
    expect(mod.MENU_CHILDREN_FALLBACK["/knowledge"]).toHaveLength(2);
    expect(mod.MENU_CHILDREN_FALLBACK["/query"]).toHaveLength(1);
  });
});

describe("getMenuTitle 工具函数", () => {
  it("优先使用 meta.title", async () => {
    const { getMenuTitle } = await import("@/constants/router.js");
    expect(getMenuTitle({ meta: { title: "自定义" }, path: "/x" })).toBe("自定义");
  });

  it("无 meta 时使用 MENU_PATH_TITLE_MAP 兜底", async () => {
    const { getMenuTitle } = await import("@/constants/router.js");
    expect(getMenuTitle({ path: "/chat/list", name: "chatList" })).toBe("AI 对话");
  });

  it("无 path 兜底时使用 name", async () => {
    const { getMenuTitle } = await import("@/constants/router.js");
    expect(getMenuTitle({ path: "/unknown", name: "unknown" })).toBe("unknown");
  });

  it("空对象返回空字符串", async () => {
    const { getMenuTitle } = await import("@/constants/router.js");
    expect(getMenuTitle(null)).toBe("");
    expect(getMenuTitle({})).toBe("");
  });
});

describe("checkResStatus 状态码处理", () => {
  it("函数存在且可被调用不抛错", async () => {
    const mod = await import("@/api/helper/checkResStatus.js");
    expect(typeof mod.checkResStatus).toBe("function");
    expect(() => mod.checkResStatus(401)).not.toThrow();
    expect(() => mod.checkResStatus(500)).not.toThrow();
  });
});

describe("组件挂载", () => {
  it("占位组件可挂载并渲染内容", () => {
    const Comp = {
      template: '<div class="placeholder">Placeholder</div>'
    };
    const wrapper = mount(Comp);
    expect(wrapper.find(".placeholder").text()).toBe("Placeholder");
  });

  it("带 props 的组件正确渲染", () => {
    const Comp = {
      template: '<div class="label">{{ label }}</div>',
      props: { label: { type: String, default: "" } }
    };
    const wrapper = mount(Comp, { props: { label: "Hello" } });
    expect(wrapper.text()).toBe("Hello");
  });

  it("组件可响应 props 变化", async () => {
    const Comp = {
      template: "<div>{{ count }}</div>",
      props: { count: { type: Number, default: 0 } }
    };
    const wrapper = mount(Comp, { props: { count: 1 } });
    expect(wrapper.text()).toBe("1");
    await wrapper.setProps({ count: 2 });
    expect(wrapper.text()).toBe("2");
  });
});
