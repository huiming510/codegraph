# -*- coding: utf-8 -*-
"""
# @Time    : 2025/12/15 09:44
# @Author  : cuils
# @Description:
"""
import aiohttp
import requests

# TODO LIST:
# 1.增加流式返回
# 2.工具调用


class OpenAIModel:
    def __init__(self,
        model: str,
        base_url: str = None,
        api_key: str = "EMPTY",
        thinking: bool = False,
        stream: bool = False,
        max_model_len: int = 4096,
        max_retry: int = 3
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.max_model_len = max_model_len

        import openai
        self.client = openai.Client(
            base_url=base_url,
            api_key=api_key
        )
        self.model = model
        self.stream = stream
        self.thinking = thinking
        self.max_retry = max_retry

    def __call__(self, messages: list[dict], **kwargs):
        retry = 0
        while retry < self.max_retry:
            try:
                resp = self.client.chat.completions.create(messages=messages, model=self.model, **kwargs, timeout=300)
                content = resp.choices[0].message.content
                if self.thinking:
                    content = content.split("</think>")[-1]
                return content
            except Exception as e:
                print(repr(e))
                retry += 1
        return None

    def get_tokens_count(self, messages: list[dict]=None, prompt: str=None):
        url = self.base_url.split("/v1")[0] + "/tokenize"
        payload = {
            "model": self.model,
        }
        if messages:
            payload["messages"] = messages
        else:
            payload["prompt"] = prompt

        count = requests.post(url, json=payload).json()["count"]
        return int(count)

    def close(self):
        self.client.close()


class AsyncOpenAIModel:
    def __init__(self,
        model: str,
        base_url: str = None,
        api_key: str = "EMPTY",
        max_model_len: int = 4096,
        thinking: bool = False,
        stream: bool = False,
        max_retry: int = 3
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.max_model_len = max_model_len

        import openai
        self.client = openai.AsyncClient(
            base_url=base_url,
            api_key=api_key
        )
        self.model = model
        self.stream = stream
        self.thinking = thinking
        self.max_retry = max_retry

    async def __call__(self, messages: list[dict], **kwargs):
        retry = 0
        while retry < self.max_retry:
            try:
                resp = await self.client.chat.completions.create(messages=messages, model=self.model, **kwargs, timeout=300)
                content = resp.choices[0].message.content
                if self.thinking:
                    content = content.split("</think>")[-1]
                return content
            except Exception as e:
                print(repr(e))
                retry += 1
        return None

    async def stream_call(self, messages: list[dict], **kwargs):
        try:
            stream = await self.client.chat.completions.create(messages=messages, model=self.model, stream=True, **kwargs, timeout=300)
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            yield repr(e)

    async def get_tokens_count(self, messages: list[dict]=None, prompt: str=None):
        url = self.base_url.split("/v1")[0] + "/tokenize"
        payload = {
            "model": self.model,
        }
        if messages:
            payload["messages"] = messages
        else:
            payload["prompt"] = prompt

        async with aiohttp.ClientSession() as session:
            retry = 0
            while retry < self.max_retry:
                try:
                    async with session.post(url, json=payload) as resp:
                        result = await resp.json()
                        return int(result["count"])
                except:
                    retry += 1
        return None

    async def close(self):
        await self.client.close()