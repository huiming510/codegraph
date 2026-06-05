# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/18
# @Author  : cuils
# @Description:
"""
import re
import json
import openai
from src.index import Retriever, VllmEmbedding, ElasticsearchClient

client = openai.Client(base_url="http://172.27.99.3:8031/v1", api_key="EMPTY")

model = client.models.list().data[0].id



retriever = Retriever(
    embedding_client=VllmEmbedding(url="http://192.168.10.187:5002/v1/embeddings", model="Qwen3-Embedding-0.6B"),
    es_client=ElasticsearchClient(url="http://192.168.10.187:9200", index="demo")
)


#*************************** query改写 ***************************
rewrite_query_prompt = """
请根据提供的用户需求描述，生成几个`query`, 用于检索与用户需求相关文档。检索文档除代码数据外，均为日语。
用户需求可能是英语、中文或日语，你可能需要将用户需求翻译成日语再进行生成。
你可以将用户需求拆解、翻译、改写和联想，但是生成的query必须和用户需求相关，检索到的文档会合并处理。要求直接返回改写的query。
返回格式：
q1: xxx
q2: xxx
q3: xxx
...

{description}
"""

desc = "前払いセルフ会計模式中，サブメニュー登录的时候，主メニュー和子メニュー的税率不一样，计算税的时候一定是根据各自的税率计算的吗？"
messages = [
    {"role": "user", "content": rewrite_query_prompt.format(description=desc)},
]

resp = client.chat.completions.create(messages=messages, model=model)
queries = [q.split(":")[-1].strip() for q in resp.choices[0].message.content.strip().split("\n")] + [desc]
print(queries)

#*************************** query检索 ***************************
documents = []
for query in queries:
    sources = retriever.retrieve(query, top_k=20)
    documents.extend(sources)
print(len(documents))

#*************************** 结果重排 ***************************
# TODO结果去重重排，这里直接按照检索分数重拍
chunk_ids = set()
res = []
for chunk in documents:
    if chunk["chunk_id"] in chunk_ids:
        continue
    res.append(chunk)
    chunk_ids.add(chunk["chunk_id"])

documents = sorted(res, key=lambda x: x["score"], reverse=True)[:20]

#*************************** 其他检索方式 ***************************
# 树结构
# 图结构

#*************************** prompt增强 ***************************

augment_prompt = """
我将提供给你一段用户需求，以及根据用户需求检索到的相关文档，请根据这些文档回答用户的问题。
请注意，如果检索的文档中没有用户需要的答案，请返回 `none`，禁止自己编造答案。
如果存在，请一并返回存在用户问题答案的文档id，文档id使用格式为 [id]

# 用户问题：
{question}

# 文档：
{documents}
"""
contents = []
for i, doc in enumerate(documents):
    content = f"[{i+1}]:\n{doc["content"]}"
    contents.append(content)

for doc in documents:
    print(doc["chunk_id"], doc["score"])


#*************************** 生成回复 ***************************
messages = [
    {"role": "user", "content": augment_prompt.format(question=desc, documents="\n\n".join(contents))}
]

resp = client.chat.completions.create(messages=messages, model=model)

result = resp.choices[0].message.content
print(result)
# 识别参考文档
indices = re.findall(r"\[(\d+)\]", result)

for _id in indices:
    print(documents[int(_id)-1]["chunk_id"])