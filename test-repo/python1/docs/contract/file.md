## File文件相关
### 文件上传
POST /file/upload  
Content-Type: application/json  
- 请求参数

| 参数       | 类型     | 说明                       |
|----------|--------|--------------------------|
| doc_id   | string | 文件id                     |
| filepath | string | 文件绝对路径，保证该文件路径和后端服务在同一机器 |
| index    | string | 写入索引知识库名称                |

- 返回参数

| 参数     | 类型     | 说明        |
|--------|--------|-----------|
| doc_id | string | 文件id      |
| status | int    | 正常返回202   |
| index  | str    | 写入索引知识库名称 |
| msg    | str    | 返回信息      |


### 文件流上传
POST /file/upload_stream  
Content-Type: multipart/form-data   
**不支持** application/json  
- 请求参数

| 文本字段参数 | 类型     | 说明        |
|--------|--------|-----------|
| doc_id | string | 文件id      |
| index  | string | 写入知识库索引名称 |

| 文件字段参数 | 类型     | 说明   |
|--------|--------|------|
| file   | binary | 文件流  |

- 返回参数

| 参数     | 类型     | 说明        |
|--------|--------|-----------|
| doc_id | string | 文件id      |
| status | int    | 正常返回202   |
| index  | str    | 写入知识库索引名称 |
| msg    | str    | 返回信息      |

### 2.2 文件删除
暂不支持
### 2.3 文件一览
暂不支持