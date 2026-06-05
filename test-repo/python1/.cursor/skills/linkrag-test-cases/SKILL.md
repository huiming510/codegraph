---
name: linkrag-test-cases
description: 为 LinkRAG 前后端生成单元/疏通/集成测试用例，支持 TDD（先写失败用例再实现）。在用户要求「写测试」「疏通测试」「单元测试」「集成测试」「TDD」时使用。
---

# LinkRAG 测试用例生成

按 [测试策略与用例生成](docs/测试策略与用例生成.md) 的分层：**单元 / 疏通 / 集成**。用户未明确层级时默认生成**疏通用例**；明确「单元」或「集成」或「TDD」时按对应规则生成。

## 使用场景

- **疏通**：「给 xxx 模块加测试」「疏通测试」「smoke test」「功能做完写测试」→ 主路径 200、页面可挂载
- **单元**：「为 xxx 函数/组件写单元测试」「单元测试」→ 单函数/单组件 + mock 外部
- **集成**：「集成测试」「按验收写流程测试」→ 跨模块、关键流程端到端
- **TDD**：「按 TDD」「先写测试」→ 先写失败用例，再提示用户实现

## 原则

- **疏通优先**：未指定层级时，生成疏通用例（接口 200、页面挂载），保证主路径可跑通。
- **最小依赖**：后端 pytest + TestClient/httpx；前端 Vitest + @vue/test-utils；与项目现有 conftest、目录一致。
- **与项目一致**：路由前缀、请求体、前端 API/路由、测试目录见 [测试体系](docs/测试体系.md)。

---

## 调用本技能前建议准备（辅助材料）

生成质量依赖以下材料是否齐全；至少具备「接口/路由 + 主要 view」即可生成疏通用例。

| 材料 | 用途 |
|------|------|
| **API 文档（含响应约定）** | **接口测试唯一依据**：断言 `code`、`data` 必须以 [API文档 1.2](docs/API文档.md) 为准；成功时 `code==0`，勿用 `code==200` |
| **需求/验收文档**（含验收 ID，如 REQ-001） | 集成用例、TDD 用例、用例与需求追溯 |
| **接口/路由清单**（路径、方法、需否 token） | 疏通用例：哪些接口要 200 |
| **前端路由与主要 view 列表** | 疏通用例：哪些页面要挂载、关键元素 |
| **带注释的代码**（docstring/JSDoc：用途、参数、返回） | 单元/疏通：边界与断言更准确；见 [代码注释规则](.cursor/rules/code-comments.mdc) |
| **现有 conftest / fixture** | 生成风格与 client、auth_headers 一致 |

**文档与测试依据**：**文档不全则用例易错**。接口断言必须以 API 文档为准；需求或验收应先有记录，测试才有「预期行为」可依；详见 [测试策略与用例生成 - 四、五节](docs/测试策略与用例生成.md)。

---

## 后端测试（FastAPI）

### 技术选型

- **框架**：pytest
- **客户端**：`httpx` + `ASGITransport` 调用 FastAPI app（异步），或 `fastapi.testclient.TestClient`（同步，简单场景足够）
- **位置**：`src/backend/tests/`（若不存在则创建）
- **约定**：`conftest.py` 提供 `client` fixture；按路由模块分文件，如 `test_auth.py`、`test_knowledge_bases.py`

### 依赖

项目 `requirements.txt` 中已有 `httpx`、`fastapi`。需**额外安装**（开发/测试用）：

```bash
pip install pytest pytest-asyncio
```

可选：在 `src/backend/requirements-dev.txt` 或文档中注明上述依赖。

### conftest 要点

- 使用 FastAPI 的 `app`（从 `main` 导入），可用内存 SQLite 或 test 配置避免动生产库。
- 提供同步 `client`（TestClient）或异步 `async_client`（httpx.AsyncClient + ASGITransport）。
- 若接口需要登录：在 conftest 或 test 内先调登录接口拿到 token，后续请求带 `Authorization: Bearer <token>`。

### 用例内容建议

- **auth**：登录成功 200、错误密码 401、登出或菜单 200（需 token）。
- **knowledge-bases**：列表 200、创建 200、获取单条 200、删除 200（按需带 token）。
- **documents / upload**：上传/列表/状态 等关键接口 200。
- **其他 router**：每个模块至少 1～2 个「主路径 200」的 test，保证疏通。

### 运行方式

```bash
cd src/backend
pytest tests/ -v
# 或指定文件
pytest tests/test_auth.py -v
```

---

## 前端测试（Vue 3 + Vite）

### 技术选型

- **框架**：Vitest（与 Vite 同源，配置简单）
- **组件测试**：`@vue/test-utils`
- **位置**：`src/frontend/src/**/__tests__/*.spec.js` 或 `src/frontend/tests/`（与项目约定一致即可）
- **约定**：单文件命名 `*.spec.js` 或 `*.spec.ts`，与待测组件/页面同目录或集中放 tests 目录

### 依赖

当前 `package.json` 可能未包含测试库，生成测试时如未安装需说明安装：

```bash
cd src/frontend
npm install -D vitest @vue/test-utils jsdom
```

并在 `package.json` 的 `scripts` 中增加：

```json
"test": "vitest",
"test:run": "vitest run"
```

必要时在根目录或 `src/frontend` 增加 `vitest.config.js`（或合并进 `vite.config.js` 的 test 配置）。

### 用例内容建议

- **页面/视图**：对主要 `views` 做「可挂载」测试：`mount(Component)` 不抛错，关键文案或元素存在（如 `find('...')`）。
- **API 模块**：可对封装函数做 mock：mock `@/api` 的 request，调用 `getXxxList()` 等，断言请求参数或返回结构（疏通级别即可）。
- **Store**：若该模块强依赖某 store，可 mock store 或提供最小 state，保证组件能渲染。

### 运行方式

```bash
cd src/frontend
npm run test        # watch
npm run test:run    # 单次
```

---

## 分层生成要点

- **单元**：后端单函数/路由逻辑用 mock（如 `patch` get_db、外部 HTTP）；前端单组件/store 用 mock API 与 router。放在 `tests/unit/` 或同包下 `*_test.py` / `*.spec.js`。
- **疏通**：后端 `test_xxx.py` 用现有 conftest 的 client/auth_headers，主接口 200；前端挂载 + 关键元素存在。当前 CI 门禁以疏通为主。
- **集成**：后端多路由 + 测试库（或内存 DB）；可放在 `tests/integration/`。前端可对本地后端或 contract 测试。
- **TDD**：先根据需求/接口写出**预期行为**的测试（此时应失败），再提示用户实现；用例描述可带需求 ID（如 REQ-001）便于追溯。

## 生成步骤（给 Agent 的执行清单）

1. **确认层级与范围**：用户是否明确单元/疏通/集成/TDD；后端/前端/两者。
2. **后端**：
   - 若无 `src/backend/tests/conftest.py`，先写 conftest（client、auth_headers、测试库路径）。
   - 疏通：按路由模块 `test_xxx.py`，每模块 1～2 个主路径 200。
   - 单元：按函数/路由生成，mock DB 与外部，放 `tests/unit/` 或约定位置。
   - 集成：按流程生成，放 `tests/integration/`，注明依赖（测试库/ES）。
3. **前端**：
   - 疏通：挂载 + 关键元素；单元：单组件/函数 + mock；集成：按需。
   - 用例位置与 vite test 配置见 [测试体系](docs/测试体系.md)。
4. **收尾**：说明如何运行（`pytest src/backend/tests`、`npm run test:run`），并提醒依赖与 [测试策略与用例生成](docs/测试策略与用例生成.md) 中的追溯（需求 ID、接口对应）。

---

## Reference

- **策略与分层**：`docs/测试策略与用例生成.md`（单元/疏通/集成、自动生成策略、TDD）
- **目录与运行**：`docs/测试体系.md`、`src/backend/README.md`、`src/backend/routers/`、`src/frontend/src/api/modules/`
