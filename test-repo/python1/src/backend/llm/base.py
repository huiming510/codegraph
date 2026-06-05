"""LLM基类定义"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from pydantic import BaseModel
from enum import Enum


class LLMProvider(str, Enum):
    """支持的LLM提供商"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    ZHIPU = "zhipu"  # 智谱AI
    QWEN = "qwen"    # 通义千问
    BAIDU = "baidu"  # 文心一言
    MOCK = "mock"    # 模拟测试


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: LLMProvider = LLMProvider.MOCK
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    # Azure专用
    azure_deployment: Optional[str] = None
    azure_api_version: Optional[str] = "2024-02-01"
    # 额外参数
    extra_params: Dict[str, Any] = {}


class Message(BaseModel):
    """对话消息"""
    role: str  # system, user, assistant
    content: str


class LLMResponse(BaseModel):
    """LLM响应"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class BaseLLM(ABC):
    """LLM基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        """同步对话"""
        pass
    
    @abstractmethod
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """流式对话"""
        pass
    
    async def simple_chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """简单对话接口"""
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        response = await self.chat(messages)
        return response.content
    
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        return self.config.provider.value
