"""阿里通义千问 LLM实现"""
from typing import List, AsyncIterator
from ..base import BaseLLM, LLMConfig, Message, LLMResponse


class QwenLLM(BaseLLM):
    """阿里通义千问模型"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            from openai import AsyncOpenAI
            # 通义千问兼容OpenAI API
            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                timeout=self.config.timeout,
            )
        except ImportError:
            raise ImportError("请安装openai: pip install openai")
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.config.model or "qwen-turbo",
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            **self.config.extra_params,
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
        stream = await self.client.chat.completions.create(
            model=self.config.model or "qwen-turbo",
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            stream=True,
            **self.config.extra_params,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
