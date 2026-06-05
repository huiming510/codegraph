# 多语言文案

与 `globalStore.language`（zh / en / ja）及后端 `/api/config/locale` 对应。切换语言后界面会按当前语言显示。

## 使用

在组件中：

```js
import { useLocale } from "@/composables/useLocale";

const { t, locale } = useLocale();
// 模板中: {{ t("layout.theme") }}
// 需响应语言切换时，在模板中使用 locale 作为依赖，如 :key="locale"
```

## 文案键

- `layout.*`：布局/风格切换
- `lang.*`：语言名称与切换提示
- `common.*`：确定、取消、温馨提示
- `user.*`：个人信息、修改密码、退出登录
- `auth.*`：登录/注册、占位符、成功提示

新增文案时在 `zh.js`、`en.js`、`ja.js` 中同步添加相同 key，缺省回退到中文。
