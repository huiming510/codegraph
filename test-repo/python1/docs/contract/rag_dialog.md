## RAG多轮问答（流式）
### 多轮问答
POST /chat/stream  
Content-Type: application/json  
Accept: text/event-stream  

- 请求参数

| 参数               | 类型     | 必选 | 备注          |
|------------------|--------|----|-------------|
| session_id       | string | 是  | 会话id        |
| utterance        | string | 是  | 用户utterance |
| index            | string | 是  | 知识库索引名称     |
| search_options   | dict   | 否  | 搜索参数        |
| generate_options | dict   | 否  | 生成参数        |

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

- 返回：采用SSE事件流式返回

| event      | 类型               | 说明                          |
|------------|------------------|-----------------------------|
| session_id | string           | 当前对话的会话id，必选事件              |
| start      | string           | 答案流式返回开始事件，必选事件             |
| delta      | Optional[string] | 块内容，非必选事件                   |
| end        | string           | 答案流式返回结束事件，必选事件             |
| references | json-string      | 参考片段列表，json格式，非必选事件         |
| error      | string           | 错误信息，非必选事件                  |
| done       | string           | 请求结束事件，该事件数据固定为 [DONE]，必选事件 |

* reference

| 字段        | 类型     | 说明              |
|-----------|--------|-----------------|
| ref_id    | int    | 该参考片段在答案中的引用id  |
| chunk_id  | string | 该片段在知识库中的id     |
| doc_id    | string | 该片段所在的文章id      |
| content   | string | 该片段文本内容         |
| metadata | dict   | 文件名称、sheet名称等信息 |
* metadata中必存在 `file_name` 字段