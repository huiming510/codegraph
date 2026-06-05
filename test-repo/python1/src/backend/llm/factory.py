"""LLM工厂类"""
from typing import Optional
from .base import BaseLLM, LLMConfig, LLMProvider


class LLMFactory:
    """LLM工厂 - 根据配置创建对应的LLM实例"""
    
    _providers = {}
    
    @classmethod
    def register(cls, provider: LLMProvider, llm_class):
        """注册LLM提供商"""
        cls._providers[provider] = llm_class
    
    @classmethod
    def create(cls, config: LLMConfig) -> BaseLLM:
        """创建LLM实例"""
        # 延迟导入，避免循环依赖
        if not cls._providers:
            cls._register_all()
        
        provider = config.provider
        if provider not in cls._providers:
            raise ValueError(f"不支持的LLM提供商: {provider}")
        
        return cls._providers[provider](config)
    
    @classmethod
    def _register_all(cls):
        """注册所有提供商"""
        from .providers import (
            OpenAILLM,
            AzureOpenAILLM,
            AnthropicLLM,
            OllamaLLM,
            ZhipuLLM,
            QwenLLM,
            MockLLM,
        )
        cls.register(LLMProvider.OPENAI, OpenAILLM)
        cls.register(LLMProvider.AZURE_OPENAI, AzureOpenAILLM)
        cls.register(LLMProvider.ANTHROPIC, AnthropicLLM)
        cls.register(LLMProvider.OLLAMA, OllamaLLM)
        cls.register(LLMProvider.ZHIPU, ZhipuLLM)
        cls.register(LLMProvider.QWEN, QwenLLM)
        cls.register(LLMProvider.MOCK, MockLLM)
    
    @classmethod
    def list_providers(cls) -> list:
        """列出所有支持的提供商"""
        return [p.value for p in LLMProvider]


# 全局LLM实例
_llm_instance: Optional[BaseLLM] = None


def get_llm(config: Optional[LLMConfig] = None) -> BaseLLM:
    """获取LLM实例（单例模式）"""
    global _llm_instance
    if _llm_instance is None or config is not None:
        if config is None:
            # 默认使用Mock
            config = LLMConfig(provider=LLMProvider.MOCK)
        _llm_instance = LLMFactory.create(config)
    return _llm_instance


def reset_llm():
    """重置LLM实例"""
    global _llm_instance
    _llm_instance = None
