import { onMounted, onUnmounted } from "vue";

/**
 * 快捷键 Hook
 * @param {string|string[]} keys - 快捷键，可以是单个字符串或数组（组合键）
 * @param {Function} callback - 按下时执行的函数
 * @param {Object} options - 配置项
 * @param {boolean} options.preventDefault - 是否阻止默认事件（默认 true）
 * @param {boolean} options.capture - 是否在捕获阶段监听（默认 true，避免浏览器抢先）
 */
export function useShortcut(keys, callback, options = { preventDefault: true, capture: true }) {
  const normalizedKeys = Array.isArray(keys) ? keys.map(k => k.toLowerCase()) : [keys.toLowerCase()];

  const handler = event => {
    const pressedKeys = [];

    if (event.ctrlKey) pressedKeys.push("ctrl");
    if (event.shiftKey) pressedKeys.push("shift");
    if (event.altKey) pressedKeys.push("alt");
    if (event.metaKey) pressedKeys.push("meta");

    // 普通键
    const mainKey = event.key.toLowerCase();
    if (!["ctrl", "shift", "alt", "meta"].includes(mainKey)) {
      pressedKeys.push(mainKey);
    }

    // 检查是否匹配
    if (normalizedKeys.sort().join("+") === pressedKeys.sort().join("+")) {
      if (options.preventDefault) event.preventDefault();
      callback(event);
    }
  };

  onMounted(() => window.addEventListener("keydown", handler, { capture: options.capture }));
  onUnmounted(() => window.removeEventListener("keydown", handler, { capture: options.capture }));
}
