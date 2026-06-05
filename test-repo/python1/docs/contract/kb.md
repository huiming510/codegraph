## DB索引相关
### 创建索引  
PUT /index/create  
Content-Type: application/json  

- 请求参数

|参数|类型| 说明           |
|---|---|--------------|
|index|string| 新建知识库索引名称，必选 |

- 返回参数

| 参数     | 类型  | 说明           |
|--------|-----|--------------|
| status | int | 200成功；其他值为失败 |
| msg    | str | 返回信息         |

### 删除索引  
DELETE /index/delete  

- 请求参数

|参数|类型| 说明           |
|---|---|--------------|
|index|string| 删除知识库索引名称，必选 |

```shell
DELETE /index/delete?index=ddd
```

- 返回参数

| 参数     | 类型  | 说明        |
|--------|-----|-----------|
| status | int | 200成功；其他值为失败 |
| msg    | str | 返回信息      |

### 查看索引  
POST /index/info   
- 请求参数

|参数|类型| 说明           |
|---|---|--------------|
|index|string| 查看知识库索引名称，必选 |

- 返回参数

| 参数     | 类型  | 说明        |
|--------|-----|-----------|
| status | int | 200成功；其他值为失败 |
| msg    | str | 返回信息      |