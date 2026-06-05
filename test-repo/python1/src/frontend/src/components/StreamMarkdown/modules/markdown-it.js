/**
 * markdown-it 配置模块
 * 用于配置 Markdown 解析器，包含插件和渲染选项
 */

import MarkdownIt from "markdown-it";

/**
 * markdown-it 配置选项
 */
const config = {
  html: true,
  xhtmlOut: true,
  breaks: true,
  langPrefix: "lang-",
  linkify: false,
  typographer: true,
  quotes: "\"\"''"
};

/**
 * 创建并配置 markdown-it 实例
 * @returns {Promise<MarkdownIt>} 配置完成的 markdown-it 实例
 */
async function createMarkdownIt() {
  const markdownIt = new MarkdownIt(config);

  // 加载基本的markdown插件
  try {
    // 任务列表插件 - 支持 [ ] 和 [x] 语法
    const taskLists = (await import("markdown-it-task-lists")).default;
    markdownIt.use(taskLists);
  } catch (error) {
    console.warn("Task lists plugin failed to load:", error);
  }

  return markdownIt;
}

// 创建并导出单例实例
let markdownItInstance = null;

const getMarkdownIt = async () => {
  if (!markdownItInstance) {
    markdownItInstance = await createMarkdownIt();
  }
  return markdownItInstance;
};

export default getMarkdownIt;
