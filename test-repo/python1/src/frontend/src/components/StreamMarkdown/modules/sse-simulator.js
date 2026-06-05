/**
 * SSE 模拟器模块
 * 模拟 Server-Sent Events 流式返回内容
 */

/**
 * 创建SSE生成器
 * @param {string} content 要流式返回的内容
 * @param {Object} options 配置选项
 * @param {number} options.minChunkSize 最小块大小，默认1
 * @param {number} options.maxChunkSize 最大块大小，默认20
 * @param {number} options.delay 每次返回的延迟时间，默认20ms
 * @returns {Generator} 生成器函数
 */
export function* createSSEGenerator(content, options = {}) {
  const { minChunkSize = 1, maxChunkSize = 20, delay = 20 } = options;

  let i = 0;
  while (i < content.length) {
    // 随机生成指定范围内的数
    const chunkSize = Math.floor(Math.random() * (maxChunkSize - minChunkSize + 1)) + minChunkSize;
    // 获取一个片段
    const chunk = content.slice(i, i + chunkSize);
    yield chunk; // 一次性返回这部分字符
    i += chunkSize; // 更新索引，跳过已经返回的字符
    // 休眠指定时间
    yield new Promise(resolve => setTimeout(resolve, delay));
  }
}

/**
 * 处理 SSE 返回的内容
 * @param {Generator} generator 生成器实例
 * @param {Object} callbacks 回调函数
 * @param {Function} callbacks.onContent 接收到内容时的回调
 * @param {Function} callbacks.onComplete 完成时的回调
 * @param {Function} callbacks.onError 错误时的回调
 */
export function processSSEStep(generator, callbacks = {}) {
  const { onContent, onComplete, onError } = callbacks;

  // 获取生成迭代对象
  const result = generator.next();

  // 生成器结束
  if (result.done) {
    if (onComplete) onComplete();
    return;
  }

  if (result.value instanceof Promise) {
    // 如果值是 Promise，等待它完成再继续
    result.value
      .then(() => {
        // 无意义的结果, 继续执行下一个步骤
        processSSEStep(generator, callbacks);
      })
      .catch(error => {
        if (onError) onError(error);
        else console.error("Error occurred during promise resolution:", error);
      });
  } else {
    // 将当前的部分内容加入队列进行渲染
    // 这个时候拿到的 result.value 是 string 是有意义的结果,用来处理具体逻辑
    if (onContent) onContent(result.value);
    // 继续下一步
    processSSEStep(generator, callbacks);
  }
}

/**
 * 开始 SSE 模拟
 * @param {string} content 要流式返回的内容
 * @param {Object} options 配置选项
 * @param {Object} callbacks 回调函数
 */
export function startSSESimulation(content, options = {}, callbacks = {}) {
  const generator = createSSEGenerator(content, options);
  // 开始处理生成器的每一步
  processSSEStep(generator, callbacks);
}
