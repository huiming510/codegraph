# -*- coding: utf-8 -*-
"""
# @Time    : 2025/12/5 15:02
# @Author  : cuils
# @Description:
"""
import json
import openai
import asyncio
from src.index import VllmEmbedding, AsyncElasticsearchClient, AsyncRetriever


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve",
            "description": "知识库检索，返回和请求的query相关的文档",
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "description": "用户检索的query列表",
                    }
                },
                "required": ["queries"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete",
            "description": "如果你确认解答了用户的问题，则使用该function，否则不要使用该工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string",
                        "description": "仅包含用户解答用户问题的详细答案，该参数禁止包含任何解释说明。"
                    }
                },
                "required": ["result"]
            }
        }
    }
]


SYSTEM_PROMPT = """
## Role
你是Finder，擅长知识搜索、信息推理、知识汇总，以及使用外部工具。

## Task
分析用户任务需求，思考需要获取哪些知识回答用户问题；针对需要的知识，生成合理的query，用来检索知识库。获取到知识后，进行归纳整理，回答用户的需求。
当获取的知识不充分或不可用时，及时修改query，直到能完全回答用户的任务需求。
当用户需求不需要知识检索时，直接调用`complete`工具返回你的答案即可。

## Requirements
1. 生成query的数量必须不少于 5 个，且query不能存在语义相似，保证有效率的获取更全面、准确的信息。
2. 仔细分析、理解用户任务需求，对于复杂的任务需求，可以进行任务拆解。对于模糊的需求，可以进行联想。
3. 知识库中的文档，除代码外，均为日语，为了保证有效检索，生成的query必须为日语。
4. 每次回复，你必须调用外部工具。如果解决了用户的问题，必须调用`complete`工具。若没有完成用户任务，禁止调用`complete`工具。
5. 当需要重新生成query时，新的query不能和历史query相同或存在语义上的相似。
"""


retriever = AsyncRetriever(
    embedding_client=VllmEmbedding(url="http://192.168.10.187:5002/v1/embeddings", model="Qwen3-Embedding-0.6B"),
    es_client=AsyncElasticsearchClient(url="http://elastic:+ZWNahlRPSAwNj2g5Upr@192.168.10.187:9200", index="poc")
)

llm = openai.AsyncClient(
    base_url="http://192.168.10.187:5005/v1",
    api_key="EMPTY"
)
model = "Qwen3-30B-A3B-Thinking-2507"
thinking = True

async def retrieve(queries):
    """检索模块"""
    async_results = await retriever.parallel_retrieve(queries, top_k=10)
    documents = []
    for _, sources in async_results:
        documents.extend(sources)
    return documents


async def complete(result):
    """任务完成，必须调用该方法返回结果"""
    return result


async def run(user_input):
    contexts = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    loop = 0

    while loop < 5:
        resp = await llm.chat.completions.create(
            messages=contexts,
            model=model,
            tool_choice="auto",
            tools=TOOLS
        )
        loop += 1
        content = resp.choices[0].message.content
        if thinking:
            content = content.split("</think>")[-1]
        assistant_message = {
            "role": "assistant",
            "content": content,
            "tool_calls": resp.choices[0].message.tool_calls
        }
        contexts.append(assistant_message)

        if not resp.choices[0].message.tool_calls:
            message = "[Error]：你没有调用任何工具。如果你确认已经完成了任务，请调用`complete`工具；如果没有，则按照任务要求继续执行。"
            contexts.append({"role": "user", "content": message})
            continue

        print("message:", resp.choices[0].message.content)
        tool_call = resp.choices[0].message.tool_calls[0]
        function_name = tool_call.function.name
        function_arguments = tool_call.function.arguments
        print(function_name, function_arguments)

        if function_name == "retrieve":
            documents = await retrieve(**json.loads(function_arguments))
            documents = sorted(documents, key=lambda d: d["score"], reverse=True)[:10]
            references = []
            for i, doc in enumerate(documents):
                references.append(f"[{i + 1}]:\n{doc['content']}")
            references = "\n\n".join(references)
            message = f"工具：`{function_name}`, 参数：{function_arguments}, 返回结果：\n\n{references}"
            contexts.append({"role": "user", "content": message})

        elif function_name == "complete":
            return await complete(**json.loads(function_arguments))

        else:
            raise ValueError("Not found function, only `retrieve`, `complete`")

    return None


if __name__ == '__main__':
    res = asyncio.run(run("今天是星期几"))
    print(res)