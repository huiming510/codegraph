/**
 * E2E：登录、鉴权、主流程、错误页
 * 需后端 API 可用，否则登录提交会失败
 * 截图：失败时自动保存；成功时「登录页截图」保存到 test-results/screenshots/
 * 路由模式为 hash，内部路由需使用 /#/path 格式
 */
const path = require("path");
const { test, expect } = require("@playwright/test");

const H = p => (p.startsWith("#") ? p : `/#${p.startsWith("/") ? p : "/" + p}`);

test.describe("登录页", () => {
  test("打开登录页可见表单与输入框", async ({ page }) => {
    await page.goto(H("/login"));
    await expect(page.locator("form")).toBeVisible({ timeout: 10000 });
    const usernameInput = page.locator('input[type="text"]').first();
    const passwordInput = page.locator('input[type="password"]').first();
    await expect(usernameInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
  });

  test("登录页截图", async ({ page }) => {
    await page.goto(H("/login"));
    await expect(page.locator("form")).toBeVisible({ timeout: 10000 });
    const dir = path.join("test-results", "screenshots");
    require("fs").mkdirSync(dir, { recursive: true });
    await page.screenshot({ path: path.join(dir, "login-page.png"), fullPage: true });
  });

  test("登录页有登录按钮且可点击", async ({ page }) => {
    await page.goto(H("/login"));
    const btn = page.locator("form button[type=submit], form button.ant-btn-primary").first();
    await expect(btn).toBeVisible({ timeout: 10000 });
    await expect(btn).toBeEnabled();
  });

  test("完整登录流程：输入账号密码并提交，成功后跳转至主界面", async ({ page }) => {
    await page.goto(H("/login"));
    await page.locator('input[type="text"]').first().fill("admin");
    await page.locator('input[type="password"]').first().fill("admin123");
    await page.locator("form button[type=submit], form button.ant-btn-primary").first().click();
    await expect(page).toHaveURL(/\/(chat|layout|home)/, { timeout: 15000 });
    await expect(page.getByRole("main")).toBeVisible({ timeout: 8000 });
  });

  test("错误密码登录后仍停留在登录页并显示错误提示", async ({ page }) => {
    await page.goto(H("/login"));
    await page.locator('input[type="text"]').first().fill("admin");
    await page.locator('input[type="password"]').first().fill("wrongpassword");
    await page.locator("form button[type=submit], form button.ant-btn-primary").first().click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/login/);
    const msg = page.locator(".ant-message-error, .ant-message, [class*='message']");
    await expect(msg.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe("鉴权与跳转", () => {
  test("未登录访问首页会跳转到登录", async ({ page }) => {
    await page.goto(H("/"));
    await page.waitForURL(/\/(login|$)/, { timeout: 15000 });
    await expect(page.locator("form")).toBeVisible({ timeout: 5000 });
  });

  test("未登录访问 /chat 会跳转到登录", async ({ page }) => {
    await page.goto(H("/chat"));
    await page.waitForURL(/\/(login|$)/, { timeout: 15000 });
  });

  test("未登录访问 /knowledge 会跳转到登录", async ({ page }) => {
    await page.goto(H("/knowledge/knowledgeMgt"));
    await page.waitForURL(/\/(login|$)/, { timeout: 15000 });
  });
});

test.describe("登录后主流程", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(H("/login"));
    await page.locator('input[type="text"]').first().fill("admin");
    await page.locator('input[type="password"]').first().fill("admin123");
    await page.locator("form button[type=submit], form button.ant-btn-primary").first().click();
    await expect(page).toHaveURL(/\/(chat|layout|home)/, { timeout: 15000 });
  });

  test("登录后可访问知识库管理页", async ({ page }) => {
    await page.goto(H("/knowledge/knowledgeMgt"));
    await expect(page).toHaveURL(/knowledge/);
    await expect(page.locator(".knowledge-container, .empty-state").first()).toBeVisible({ timeout: 15000 });
  });

  test("登录后可访问智能检索页", async ({ page }) => {
    await page.goto(H("/query/rag"));
    await expect(page).toHaveURL(/query/);
    await expect(page.locator("form, .ant-form, [class*='query'], [class*='search']").first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("错误页", () => {
  test("访问 500 页（白名单）显示网络异常文案", async ({ page }) => {
    await page.goto(H("/500"));
    await expect(page.locator("text=/网络|不见了|500/i")).toBeVisible({ timeout: 8000 });
  });

  test("登录后访问 403 页显示无权限", async ({ page }) => {
    await page.goto(H("/login"));
    await page.locator('input[type="text"]').first().fill("admin");
    await page.locator('input[type="password"]').first().fill("admin123");
    await page.locator("form button[type=submit], form button.ant-btn-primary").first().click();
    await expect(page).toHaveURL(/\/(chat|layout|home)/, { timeout: 15000 });
    await page.goto(H("/403"));
    await expect(page.locator("text=/无权访问|403/i")).toBeVisible({ timeout: 8000 });
  });

  test("登录后访问不存在的路径显示 404", async ({ page }) => {
    await page.goto(H("/login"));
    await page.locator('input[type="text"]').first().fill("admin");
    await page.locator('input[type="password"]').first().fill("admin123");
    await page.locator("form button[type=submit], form button.ant-btn-primary").first().click();
    await expect(page).toHaveURL(/\/(chat|layout|home)/, { timeout: 15000 });
    await page.goto(H("/not-exist-xyz"));
    await expect(page.locator("text=/不存在|404/i")).toBeVisible({ timeout: 8000 });
  });
});
