# -*- coding: utf-8 -*-
"""
# @Time    : 2025/12/1 10:58
# @Author  : cuils
# @Description:
"""
CONTINUE_RETRIEVE_PROMPT = """
## Role
你是一个软件开发专家，精通中日英三种语言。熟悉日本软件开发流程和细节。

## Task
我将提供给你一段用户需求，用于检索知识文档的多个query，以及根据这些文档生成的用户需要的答案。
你需要判断生成的答案是否已经【完全】回答了用户的问题：
- 如果生成的答案已经满足用户的需求，请返回 `OK`，禁止返回其他内容。
- 如果生成的答案存在遗漏或未满足用户需求，需要进一步检索，请返回用于检索的query。

## Requirements
- 不需要返回任何解释说明，必须按照要求返回具体内容。
- 若生成query，每一行一个query。
- 禁止生成已经使用过的query，新生成的query不能和提供的query存在重叠的含义。
- 知识库中文档语言为日语，你【可能】需要生成日语的query，提高检索召回。

---
## User Input
{question}

## History Queries
{queries}

## History Answer
{answer}
"""