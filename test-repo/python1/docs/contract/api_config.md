## API设置
### 模型更新
POST /api/update_model  
Content-Type: application/json  

- 请求参数

| 参数       | 类型     | 是否必选 | 备注        |
|----------|--------|------|-----------|
| model    | string | 是    | 模型名称      |
| base_url | string | 是    | 模型url     |
| api_key  | string | 是    | api key   |
| thinking | bool   | 是    | 是否think模型 |

- 返回参数

| 参数     | 类型  | 说明           |
|--------|-----|--------------|
| status | int | 200成功；其他值为失败 |
| msg    | str | 返回信息         |

### 分块策略更新
POST /api/update_text_pipeline  
Content-Type: application/json  

- 请求参数

| 参数             | 类型     | 是否必选 | 备注                |
|----------------|--------|------|-------------------|
| index          | string |是| 知识库索引名称           |
| chunk_size     | int    | 否    | 分块大小，默认`4096`     |
| chunk_overlap  | int    | 否    | 块重叠大小，默认`256`     |
| chunk_strategy | string | 否    | 分块策略，默认 `general` |

- 返回参数

| 参数     | 类型  | 说明           |
|--------|-----|--------------|
| status | int | 200成功；其他值为失败 |
| msg    | str | 返回信息         |