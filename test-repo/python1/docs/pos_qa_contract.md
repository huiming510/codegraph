# 契约
## 1. 介绍
pos知识库问答接口

## 2. 接口
POST请求
http://192.168.89.158:8000/search

## 3. 请求参数
| 参数    | 类型     | 是否必选 | 备注           |
|-------|--------|------|--------------|
| uid   | string | 否    | 请求id，但是建议带上id |
| query | string | 是    | 用户query      |
| top_k | int    | 否    | 检索最大文档数量，默认20 |
| threshold | float  | 否    | 检索最小阈值，默认0.  |
| search_method | string | 否    | 检索方式:<br/>* dense: 仅向量检索 <br/>* dense_filter: 带过滤器的向量检索<br/>* hybrid: 混合检索（向量+BM25）<br/>* sparse:稀疏检索（仅BM25）<br/>默认 dense_filter             |

## 4. 返回参数
| 参数         | 类型           | 备注                    |
|------------|--------------|-----------------------|
| status     | int          | 返回状态 成功为200，其他值均为失败   |
| msg        | string       | 返回状态信息                |
| uid        | string       | 用户id                  |
| query      | string       | 用户query               |
| answer     | string       | 生成的答案                 |
| references | list[string] | 参考片段列表                |

## 5. 示例
* 请求示例
```python
# python

import requests

url = "http://192.168.89.158:8000/search"

query = "这是一个测试用例"

payload = {
    "query": query
}

resp = requests.post(url, json=payload)

print(resp.json())

```
* 返回示例
```json
{
    "query": "这是一个测试用例",
    "answer": "这是一个测试用例",
    "references": [
        "参考片段1",
        "参考片段2"
    ]
}
```


