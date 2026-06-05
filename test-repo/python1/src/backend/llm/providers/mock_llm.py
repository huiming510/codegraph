"""Mock LLM实现 - 用于测试"""
from typing import List, AsyncIterator
import asyncio
import random
from ..base import BaseLLM, LLMConfig, Message, LLMResponse


# 知识库内容
KNOWLEDGE_BASE = {
    "Python": "Python是一种解释型、面向对象、动态数据类型的高级程序设计语言。它具有简洁清晰的语法，易于学习和使用。Python支持多种编程范式，包括面向对象、命令式、函数式和过程式编程。",
    "机器学习": "机器学习是人工智能的一个分支，它使计算机系统能够从数据中学习并改进，而无需明确编程。主要包括监督学习、无监督学习和强化学习三大类。常见算法有决策树、神经网络、支持向量机等。",
    "FastAPI": "FastAPI是一个用于构建API的现代、快速（高性能）的Web框架，基于Python 3.6+的类型提示。它具有自动生成API文档、数据验证、异步支持等特性，性能可与NodeJS和Go媲美。",
    "Vue3": "Vue3是Vue.js的最新主要版本，引入了Composition API、更好的TypeScript支持、更快的渲染性能和更小的包体积。它采用了Proxy-based的响应式系统，提供了更灵活的组件组织方式。",
    "RAG": "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的AI技术。它先从知识库中检索相关信息，然后将检索结果作为上下文输入到大语言模型中生成回答，从而提高答案的准确性和可靠性。"
}


class MockLLM(BaseLLM):
    """模拟LLM - 用于测试和演示"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
    
    def _generate_response(self, messages: List[Message]) -> str:
        """根据消息生成模拟回复"""
        if not messages:
            return "您好！我是AI助手，有什么可以帮您的？"
        
        last_message = messages[-1].content.lower()
        
        # 匹配知识库
        for topic, content in KNOWLEDGE_BASE.items():
            if topic.lower() in last_message:
                return f"关于{topic}，{content}\n\n这些信息来自我们的知识库文档。您还想了解什么？"
        
        # 通用回复
        responses = [
            f"这是一个很好的问题！根据知识库的内容，您的问题涉及到多个方面。我可以为您提供更详细的信息，请问您想了解哪个具体方向？",
            f"我理解您的问题。基于当前知识库，我建议您可以从以下几个角度来思考：1) 基础概念 2) 实际应用 3) 最佳实践。需要我详细展开吗？",
            f"感谢您的提问！我在知识库中找到了一些相关信息。这个话题确实很有意思，您可以上传更多相关文档来获得更全面的答案。",
        ]
        return random.choice(responses)
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        # 模拟延迟
        await asyncio.sleep(0.5)
        content = self._generate_response(messages)
        return LLMResponse(
            content=content,
            model="mock-model",
            usage={
                "prompt_tokens": sum(len(m.content) for m in messages),
                "completion_tokens": len(content),
                "total_tokens": sum(len(m.content) for m in messages) + len(content),
            },
            finish_reason="stop",
        )
    
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        content = self._generate_response(messages)
        # 模拟流式输出
        for char in content:
            yield char
            await asyncio.sleep(0.02)  # 模拟打字效果
