## RAG单轮问答（非流式）
### 单轮问答  
POST /chat  
Content-Type: application/json  

- 请求参数

| 参数               | 类型     | 必选 | 备注      |
|------------------|--------|----|---------|
| session_id       | string | 是  | 会话id    |
| query            | string | 是  | 用户query |
| index            | string | 是  | 知识库索引名称 |
| search_options   | dict   | 否  | 搜索参数    |
| generate_options | dict   | 否  | 生成参数    |

**search_options**:

| 参数            | 类型     | 备注                                                                                                                        |
|---------------|--------|---------------------------------------------------------------------------------------------------------------------------|
| top_k         | int    | 检索最大文档数量，默认20                                                                                                             |
| threshold     | float  | 检索最小阈值，默认0.                                                                                                               |
| search_method | string | 检索方式:<br/>* dense: 仅向量检索 <br/>* dense_filter: 带过滤器的向量检索<br/>* hybrid: 混合检索（向量+BM25）<br/>* sparse:稀疏检索（仅BM25）<br/>默认 dense |

**generate_options**

| 参数          | 类型     | 备注   |
|-------------|--------|------|
| model       | string | 模型名称 |
| temperature | float  | 默认0.75|
| top_p       | float  | 默认0.95|

- 返回参数

| 参数         | 类型         | 备注                  |
|------------|------------|---------------------|
| status     | int        | 返回状态 成功为200，其他值均为失败 |
| msg        | string     | 返回状态信息              |
| session_id | string     | 会话id                |
| query      | string     | 用户query             |
| answer     | string     | 生成的答案               |
| references | list[dict] | 参考片段列表              |