# -*- coding: utf-8 -*-
"""
# @Time    : 2025/12/9 15:59
# @Author  : cuils
# @Description:
"""

import openai
import asyncio
from src.index import VllmEmbedding, AsyncElasticsearchClient, AsyncRetriever

retriever = AsyncRetriever(
    embedding_client=VllmEmbedding(url="http://192.168.10.187:5002/v1/embeddings", model="Qwen3-Embedding-0.6B"),
    es_client=AsyncElasticsearchClient(url="http://elastic:+ZWNahlRPSAwNj2g5Upr@192.168.10.187:9200", index="poc"),
)

llm = openai.AsyncClient(
    base_url="http://192.168.10.187:5005/v1",
    api_key="EMPTY"
)
model = "Qwen3-30B-A3B-Thinking-2507"
thinking = True

"""
循环：
query改写 -> 检索 -> 生成答案 -> 是否需要补充query -> 检索 -> 答案refine -> ... -> 最终答案
"""

FIRST_GENERATE_QUERY_PROMPT = """
## Role
你是Finder，一个信息总结、摘要助手。可以进行多跳搜索。

## Task
将用户的问题（需求）改写为适合文档检索的query。知识库中的数据为日语软件开发文档和代码。

## Requirements
- 理解用户需求，提出几个与用户需求相关的重要query，可以进行拆解、联想、翻译。
- 多个query的含义不应该重叠，比如用户需求中存在多个实体，你可以针对实体进行针对性检索。
- 如果用户问题的语种和知识库语种不一样，可能需要翻译，尽可能选择合理的翻译，来提高检索的召回率。
- 每行一个query。
- 仅输出生成的query，不需要任何解释说明

---

## User Input
{question}
"""

LOOP_GENERATE_QUERY_PROMPT = """
## Role
你是Finder，一个信息总结、摘要助手。可以进行多跳搜索。

## Task
我将提供给你一段用户问题需求、该问题的历史答案以及检索相关文档使用的历史queries。你需要判断历史答案是否已经全面回答用户的问题。
- 如果已经回答用户问题，且包含所有细节，请返回 `OK`；
- 如果历史答案缺乏某些细节，你必须针对这些缺少的内容，重新生成至多 5 个query去检索需要的文档。

## Requirements
- 生成的query为可能用于解决用户问题的、历史答案中缺乏的信息。
- 历史queries禁止重新生成，禁止出现语义上的重叠。
- 比如用户需求中存在多个实体，你可以针对实体进行针对性检索。若历史答案中出现了新的实体，且可能有助于解答用户问题，你也可以对该新实体进行检索获取信息。
- 每行一个query。
- 仅输出 `OK` 或生成的query，不需要其他的任何解释说明

---
## User Question:
{question}

## History Answer:
{history_answer}

## History Queries:
{history_queries}
"""

FIRST_GENERATE_ANSWER_PROMPT = """
## Role
你是Finder，一个信息总结、摘要助手。

## Task
我将提供给你一段用户需求、多篇检索到的相关知识文档，请根据这些文档回答用户的问题。

## Requirements
- 若文档中如果没有用户需要的答案，请返回 `None`，禁止自己编造。
- 若文档中仅包含部分答案，请将答案返回，并说明答案不完整。
- 若存在答案，必须同时返回答案参考的文档id，格式为: [id]。
- 返回结果必须使用中文。

---
## User Input:
{question}

## References:
{references}
"""

LOOP_GENERATE_ANSWER_PROMPT = """
## Role
你是Finder，一个信息总结、摘要助手。

## Task
我将提供给你一段用户问题需求、该问题的历史答案以及多篇检索到的相关知识文档，你需要根据这些文档对历史答案进行补充、修改。

## Requirements
- 若引用相关文档，必须返回引用的文档id，格式为: [id]。
- 返回结果必须使用中文。

---
## User Question:
{question}

## History Answer:
{history_answer}

## References:
{references}
"""


async def generate_queries(question, history_answer=None, history_queries=[]):
    if history_answer is None:
        messages = [
            {"role": "user", "content": FIRST_GENERATE_QUERY_PROMPT.format(question=question)},
        ]
        resp = await llm.chat.completions.create(messages=messages, model=model)
        result = resp.choices[0].message.content
        if thinking:
            result = result.split("</think>")[-1]
        queries = [q.split(":")[-1].strip() for q in result.strip().split("\n")]
        history_queries.extend(queries)

        return queries + [question]

    messages = [
        {
            "role": "user",
            "content": LOOP_GENERATE_QUERY_PROMPT.format(
                question=question,
                history_queries=history_queries,
                history_answer=history_answer
            )
        },
    ]
    resp = await llm.chat.completions.create(messages=messages, model=model)
    result = resp.choices[0].message.content
    if thinking:
        result = result.split("</think>")[-1]
    if "OK" in result:
        return None

    queries = [q.split(":")[-1].strip() for q in result.strip().split("\n")]
    history_queries.extend(queries)
    return queries


async def generate_answer(question, queries, history_answer=None):
    async_results = await retriever.parallel_retrieve(queries, top_k=10)
    documents = []
    for _, sources in async_results:
        documents.extend(sources)

    chunk_ids = set()
    _res = []
    for chunk in documents:
        if chunk["chunk_id"] in chunk_ids:
            continue
        _res.append(chunk)
        chunk_ids.add(chunk["chunk_id"])

    # 重排
    documents = sorted(_res, key=lambda x: x["score"], reverse=True)[:10]
    references = []
    for i, doc in enumerate(documents):
        references.append(f"[{i + 1}]:\n{doc['content']}")
    references = "\n\n".join(references)

    if history_answer is None:
        messages = [
            {
                "role": "user",
                "content": FIRST_GENERATE_ANSWER_PROMPT.format(
                    question=question,
                    references=references)
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": LOOP_GENERATE_ANSWER_PROMPT.format(
                    question=question,
                    history_answer=history_answer,
                    references=references)
            }
        ]

    resp = await llm.chat.completions.create(messages=messages, model=model)

    answer = resp.choices[0].message.content
    if thinking:
        answer = answer.split("</think>")[-1]

    return answer


async def main(user_input):
    history_queries = []
    history_answer = None
    max_epochs = 5

    for epoch in range(1, max_epochs + 1):
        print("-----" * 6 + f" 第{epoch}轮 " + "-----" * 6)
        # 生成query
        queries = await generate_queries(user_input, history_answer=history_answer, history_queries=history_queries)
        print(queries)
        # 判断是否需要继续生成检索生成
        if not queries:
            break

        # 生成答案
        history_answer = await generate_answer(user_input, queries, history_answer=history_answer)
        print(history_answer)

    return history_answer


if __name__ == '__main__':
    question = """ 自動釣り銭機的电源状态（PowerState）有哪些返回值"""
    # question = """1次order送信最大可以有多少个商品？"""
    # question = """前払いセルフ会計模式中，共有哪些画面？每个画面都有哪些按钮？请以表格形式列出来"""
    # question = """OPOS_PS_OFFLINE 的返回值是多少"""

    asyncio.run(main(question))
