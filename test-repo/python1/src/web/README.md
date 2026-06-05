# LinkRAG Frontend

基于 Vite 的前端项目，按 `contract/` 中接口契约实现：

- 知识库管理页面：索引管理、分块策略、文件管理
- 对话页面：模型配置、检索参数、多轮 RAG 对话（`/chat/stream` SSE）

## 本地开发

1. 安装依赖

```bash
npm install
```

2. 启动开发服务器

```bash
npm run dev
```

默认访问地址：

- [http://localhost:5173](http://localhost:5173)（知识库管理）
- [http://localhost:5173/#chat](http://localhost:5173/#chat)（对话页面，无整页刷新切换）

## 生产构建

```bash
npm run build
npm run preview
```

## 目录结构

- `index.html`：应用入口 HTML
- `chat.html`：对话页面入口 HTML
- `src/kb.js`：知识库管理逻辑
- `src/chat.js`：对话逻辑（含 SSE 流解析）
- `src/shared.js`：共享 API 工具函数
- `src/styles.css`：样式文件
- `contract/`：后端接口契约

后端 API Base URL 已内置在 `src/shared.js` 的 `API_BASE_URL` 常量中。
