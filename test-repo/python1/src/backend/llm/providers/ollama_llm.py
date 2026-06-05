"""Ollama本地LLM实现"""
from typing import List, AsyncIterator
import httpx
from ..base import BaseLLM, LLMConfig, Message, LLMResponse


class OllamaLLM(BaseLLM):
    """Ollama本地模型"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.api_base or "http://localhost:11434"
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return LLMResponse(
                content=data["message"]["content"],
                model=data["model"],
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                },
                finish_reason="stop",
            )
    
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "stream": True,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    },
                },
            ) as response:
                import json
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
