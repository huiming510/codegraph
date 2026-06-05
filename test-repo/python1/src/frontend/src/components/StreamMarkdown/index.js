/**
 * StreamMarkdown 组件导出文件
 */

export { default } from "./index.vue";
export { default as markdownIt } from "./modules/markdown-it";
export { highlightCode, buildCopyButton, buildCodeBlock, deepCloneAndUpdate } from "./modules/code-block";
export { createSSEGenerator, processSSEStep, startSSESimulation } from "./modules/sse-simulator";
