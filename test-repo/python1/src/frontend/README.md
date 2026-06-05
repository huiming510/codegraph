# RAG 前端

Vue 3 + Vite + Ant Design Vue 的 RAG 知识库管理前端。

## 环境要求

- **Node.js** >= 18.0.0（见 `package.json` 的 `engines`）
- 包管理器：**npm** / **pnpm** / **yarn** 任选其一

## 安装依赖

```bash
# 使用 npm（项目内已有 package-lock.json）
npm install

# 或使用 pnpm（项目内已有 pnpm-lock.yaml，且 .npmrc 已配置国内镜像）
pnpm install
```

若出现 `Cannot find module '...\node_modules\vite\bin\vite.js'` 或项目路径曾变更/从别处拷贝过，请先清理再安装：

```bash
# 删除依赖后重装（二选一）
Remove-Item -Recurse -Force node_modules; pnpm install
# 或
Remove-Item -Recurse -Force node_modules; npm install
```

## 启动开发环境

```bash
# 开发模式（推荐）
npm run dev
# 或
pnpm dev

# 等价于
npm run serve
```

- 默认端口：**5174**（可在 `.env.development` 中修改 `VITE_APP_PORT`）
- 默认会通过 Vite 代理将 `/api` 转发到 `http://localhost:8001`，请先启动后端服务
- 若设置了 `VITE_OPEN=true`，启动后会自动打开浏览器

访问：<http://localhost:5174>

## 环境变量说明

| 变量 | 说明 | 开发默认 |
|------|------|----------|
| `VITE_APP_NODE_ENV` | 环境：development / test / production | development |
| `VITE_APP_TITLE` | 应用标题（浏览器标题、登录页等） | RAG 知识库 |
| `VITE_APP_PUBLIC_PATH` | 部署基础路径，子路径部署时修改 | ./ |
| `VITE_APP_ROUTER_MODE` | 路由模式：hash / history | hash |
| `VITE_APP_API_BASE_URL` | 接口基础地址，开发时用 /api 走代理 | /api |
| `VITE_APP_PORT` | 开发服务器端口 | 5174 |
| `VITE_OPEN` | 是否自动打开浏览器 | true |
| `VITE_APP_PROXY` | 是否开启 /api 代理到后端 | true |

- 开发环境：复制 `.env.example` 为 `.env.development` 后按需修改，或直接使用项目内已有 `.env.development`。
- 生产构建：使用 `.env.production`；部署时可将 `VITE_APP_API_BASE_URL` 改为实际后端地址，或通过同一域名反向代理 `/api`。

## 常用脚本

| 命令 | 说明 |
|------|------|
| `npm run dev` / `pnpm dev` | 启动开发服务器 |
| `npm run build` | 生产构建（输出到 `dist/`） |
| `npm run preview` | 先构建再本地预览生产包 |
| `npm run lint` | 代码检查 |
| `npm run lint:fix` | 自动修复可修复的 lint 问题 |

## 与后端联调

1. 确保后端服务运行在 **8001** 端口（与 `vite.config.js` 中 proxy target 一致）。
2. 前端执行 `npm run dev` 或 `pnpm dev`，访问开发地址。
3. 前端请求 `/api/xxx` 会被代理到 `http://localhost:8001/api/xxx`。

若后端端口不是 8001，请修改 `vite.config.js` 中 `server.proxy["/api"].target`。

## 技术栈

- Vue 3、Vue Router、Pinia
- Vite 5
- Ant Design Vue 4
- Axios、Sass、SVG Icons（vite-plugin-svg-icons）
