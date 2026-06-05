"""Anthropic Claude LLM实现"""
from typing import List, AsyncIterator
from ..base import BaseLLM, LLMConfig, Message, LLMResponse


class AnthropicLLM(BaseLLM):
    """Anthropic Claude模型"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
            )
        except ImportError:
            raise ImportError("请安装anthropic: pip install anthropic")
    
    def _convert_messages(self, messages: List[Message]):
        """转换消息格式，提取system prompt"""
        system = None
        converted = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                converted.append({"role": m.role, "content": m.content})
        return system, converted
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        system, converted = self._convert_messages(messages)
        response = await self.client.messages.create(
            model=self.config.model,
            system=system or "",
            messages=converted,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            **self.config.extra_params,
        )
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )
    
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        system, converted = self._convert_messages(messages)
        async with self.client.messages.stream(
            model=self.config.model,
            system=system or "",
            messages=converted,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            **self.config.extra_params,
        ) as stream:
            async for text in stream.text_stream:
                yield text
