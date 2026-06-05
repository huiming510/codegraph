# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/24
# @Author  : cuils
# @Description: 
"""
import json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

es = Elasticsearch("http://elastic:+ZWNahlRPSAwNj2g5Upr@192.168.10.187:9200")

print(es.info())


def upload(items, index, batch_size=20):
    """上传数据"""
    actions = []
    for item in items:
        _action = {"_index": index, "_id": item["chunk_id"], "_source": item}
        actions.append(_action)
        if len(actions) == batch_size:
            info = bulk(es, actions=actions)
            print(info)
            actions = []
    if actions:
        info = bulk(es, actions=actions)
        print(info)


def main(fromfile):
    with open(fromfile, encoding="utf8") as f:
        items = [json.loads(line.strip()) for line in f]

    print(len(items))
    print(items[0].keys())

    # for item in items:
    #     metadata = item["metadata"]
    #     new_meta = {}
    #     if "sheet_name" in metadata:
    #         new_meta["sheet_name"] = metadata["sheet_name"]
    #     new_meta["file_name"] = metadata["file_name"]
    #     new_meta["file_absolute_path"] = metadata["文件绝对路径"]
    #     new_meta["file_desc"] = metadata["Dir /s"],
    #     new_meta["file_suffix"] = metadata["想定形式"]
    #     new_meta["business_format"] = metadata["业态"]
    #     new_meta["customer_type"] = metadata["客户体系"]
    #     new_meta["domain"] = metadata["领域分类属性"]
    #     new_meta["domain_business_type"] = metadata["领域内业态属性"]
    #     new_meta["project_name"] = metadata["工程_日文"],
    #     new_meta["project_ename"] = metadata["工程称呼"],
    #     new_meta["project_type"] = metadata["工程分类属性"]
    #
    #     item["metadata"] = new_meta

    upload(items, index="raptor")

    # resp = es.index(index="raptor", id=items[0]["chunk_id"], body=items[0])
    # print(resp)


if __name__ == '__main__':
    fromfile = f"../../examples/outputs/raptor_chunks_with_embedding.json"

    main(fromfile)
