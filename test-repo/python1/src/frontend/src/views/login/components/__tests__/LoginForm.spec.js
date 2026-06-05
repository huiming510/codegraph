/**
 * 登录表单组件测试：挂载、表单项、切换登录/注册
 */
import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import LoginForm from "../LoginForm.vue";

vi.mock("@/composables/useLocale", () => ({ useLocale: () => ({ t: k => k }) }));

const pinia = createPinia();
describe("LoginForm", () => {
  it("挂载后存在表单与用户名、密码输入", () => {
    const wrapper = mount(LoginForm, {
      global: {
        plugins: [pinia],
        mocks: { t: k => k },
        stubs: {
          UserOutlined: true,
          LockOutlined: true,
          SmileOutlined: true,
          MailOutlined: true,
          "a-form": { template: "<form><slot /></form>" },
          "a-form-item": { template: "<div><slot /></div>" },
          "a-input": { template: "<input />" },
          "a-input-password": { template: '<input type="password" />' },
          "a-button": { template: "<button><slot /></button>" },
          "a-divider": { template: "<div><slot /></div>" }
        }
      }
    });
    expect(wrapper.find("form").exists()).toBe(true);
    const inputs = wrapper.findAll("input");
    expect(inputs.length).toBeGreaterThanOrEqual(2);
  });

  it("包含登录/注册切换链接", () => {
    const wrapper = mount(LoginForm, {
      global: {
        plugins: [pinia],
        mocks: { t: k => k },
        stubs: { UserOutlined: true, LockOutlined: true, SmileOutlined: true, MailOutlined: true }
      }
    });
    expect(wrapper.text()).toMatch(/auth\.(noAccount|goRegister|hasAccount|goLogin)/);
  });
});
