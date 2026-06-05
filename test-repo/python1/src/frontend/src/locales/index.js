/**
 * 多语言文案与 t 函数
 * 与 globalStore.language (zh/en/ja) 及后端 /config/locale 对应
 */
import zh from "./zh";
import en from "./en";
import ja from "./ja";

const messages = { zh, en, ja };
const fallbackLang = "zh";

/**
 * 根据当前语言取文案，无则回退到中文
 * @param {string} lang - zh | en | ja
 * @param {string} key - 如 'layout.theme'
 * @returns {string}
 */
export function t(lang, key) {
  const map = messages[lang] || messages[fallbackLang];
  return map[key] ?? messages[fallbackLang][key] ?? key;
}

export { messages };
export default { t, messages };
