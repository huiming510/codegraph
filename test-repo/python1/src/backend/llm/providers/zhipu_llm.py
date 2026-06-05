"""智谱AI GLM LLM实现"""
from typing import List, AsyncIterator
from ..base import BaseLLM, LLMConfig, Message, LLMResponse


class ZhipuLLM(BaseLLM):
    """智谱AI GLM模型"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(api_key=self.config.api_key)
        except ImportError:
            raise ImportError("请安装zhipuai: pip install zhipuai")
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        import asyncio
        # zhipuai SDK是同步的，需要在线程池中运行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.config.model or "glm-4",
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
        )
    
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.config.model or "glm-4",
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                stream=True,
            )
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
