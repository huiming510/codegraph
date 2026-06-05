---
name: linkrag-frontend
description: Generates and modifies Vue 3 frontend code in src/frontend for the RAG knowledge base project. Follows existing request wrapper, api/modules layout, views and Pinia usage; applies distinctive frontend design guidelines to avoid generic AI aesthetics. Use when adding or changing frontend pages, API calls, or components in linkrag.
---

# LinkRAG Frontend Skill

Apply when working in **src/frontend** (Vue 3, Vite, Pinia, Ant Design Vue). Keeps code consistent with existing api, views, and router. UI should be **distinctive and production-grade**, following the design guidelines below (inspired by [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)).

## Design thinking (before coding)

- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Choose a clear direction (e.g. minimal, refined, editorial, industrial, soft/pastel) and execute it consistently. Bold maximalism and refined minimalism both work; the key is **intentionality**.
- **Differentiation**: What makes this screen or component memorable? Avoid cookie-cutter layouts and generic patterns.

Implement working code that is production-grade, visually cohesive, and meticulously refined. Match implementation complexity to the vision: maximalist needs deliberate motion and detail; minimalist needs restraint, spacing, and typography.

## Frontend aesthetics guidelines

- **Typography**: Prefer distinctive, characterful fonts. Avoid overused choices (Inter, Roboto, Arial, system-ui). Pair a display font with a refined body font. Use project `src/assets/iconfont` and `src/styles` where applicable.
- **Color & theme**: Cohesive palette; use CSS variables (e.g. in `src/styles/`). Dominant colors with sharp accents; avoid timid, evenly-distributed or clichéd schemes (e.g. purple gradients on white).
- **Motion**: Use CSS or Vue transitions for micro-interactions; consider staggered reveals (animation-delay) on load, scroll-triggered or hover states. Prefer high-impact moments over scattered effects.
- **Layout**: Consider asymmetry, overlap, grid-breaking, generous negative space or controlled density. Avoid predictable, template-like layouts.
- **Backgrounds & depth**: Prefer atmosphere and depth over flat solid colors—gradients, subtle textures, layered transparencies, shadows, or grain where they fit the aesthetic.

**Do not** default to generic AI aesthetics: overused fonts, clichéd color schemes, predictable layouts, or same-looking components. Vary light/dark, fonts, and style by context. Never converge on common defaults (e.g. Space Grotesk everywhere).

When customizing Ant Design Vue components, override tokens/variables and use scoped styles or project SCSS so the result feels designed for this product, not out-of-the-box generic.

## Scope

- **In scope**: `src/frontend` only (api/, views/, router/, stores/, components/, etc.).
- **Out of scope**: Do not change backend or other repo directories; call backend via existing API layer.

## Request layer

- All HTTP calls use the shared instance: `import request from "@/api"` (from `src/api/index.js`). Do not create another axios instance.
- baseURL is `/api`; interceptors already handle `{ code, data, msg }` and return `data` on success, show error and reject on failure. 401 triggers logout and redirect to login.
- New APIs: add methods in the right `src/api/modules/xxx.js` (e.g. knowledgeBase.js, document.js). Path = backend path **without** `/api` prefix (e.g. `request.get("/knowledge-bases", params)`).

## API module pattern

```javascript
// src/api/modules/xxx.js
import request from "@/api";
export const getXxxList = (params = {}) => request.get("/xxx", params);
export const getXxx = id => request.get(`/xxx/${id}`);
export const createXxx = data => request.post("/xxx", data);
export const updateXxx = (id, data) => request.put(`/xxx/${id}`, data);
export const deleteXxx = id => request.delete(`/xxx/${id}`);
```

## Views and routing

- Page-level components live under `src/views/` (e.g. `views/knowledge/detail/index.vue`). Feature-specific components can live under `views/xxx/components/`.
- Routes: static in `router/modules/staticRouter.js`, dynamic from backend menu in `router/modules/dynamicRouter.js`. For dynamic routes, component path must match `views` (e.g. `/src/views/xxx/index.vue`).
- Use Pinia for state (auth, user, global); do not introduce Vuex.

## Naming and style

- Components: PascalCase. File/dir names align with route path (existing project habit).
- API methods: camelCase, match backend semantics (e.g. getKnowledgeBases, createKnowledgeBase).
- Env: `import.meta.env.VITE_APP_*`; align with `.env.development` / `.env.production`. Do not disable ESLint/Prettier/Stylelint project config.

## New feature checklist

- [ ] New endpoints in appropriate `api/modules/xxx.js` using `request.get/post/put/delete`.
- [ ] New pages under `views/`, menu/route configured in static or dynamic router if needed.
- [ ] No new axios instance; do not bypass `api/index.js` interceptors.
- [ ] Use `VITE_APP_*` for env and existing lint config.

## Minimal page example

```vue
<script setup>
import { getXxxList } from "@/api/modules/xxx";
const list = ref([]);
onMounted(async () => {
  list.value = await getXxxList({ skip: 0, limit: 20 });
});
</script>
<template>
  <!-- ... -->
</template>
```

## Reference

**本 Skill 以项目文档《前端开发文档》为规范依据，实现与扩展前端时请优先参考该文档。**

- **主参考文档（必读）**：`docs/前端开发文档.md` — 技术栈、目录结构、启动与运行、环境变量、与后端联调、开发规约摘要、常用脚本；与本 Skill 的请求/路由/视图约定一致。
- 规约细则：`.cursor/rules/frontend-conventions.mdc`
- 接口与模块映射：`docs/API文档.md`
- 架构说明：`docs/开发框架说明.md`
- Skill 内快速查阅：`.cursor/skills/linkrag-frontend/reference.md`
- 设计参考（避免通用 AI 审美）：[Anthropic frontend-design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)
