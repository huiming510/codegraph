# -*- coding: utf-8 -*-
"""
# @Time    : 2025/12/11 15:20
# @Author  : cuils
# @Description:
"""
import json
import numpy as np
from elasticsearch import Elasticsearch


class TreeRetriever:
    """在构建ES索引时其实是将树压缩了，在DFS搜索时，需要还原，就是搜索范围限制在子节点的范围内"""
    def __init__(self, embedding_client, es_client: Elasticsearch):
        self.embedding_client = embedding_client
        self.es_client = es_client

    def get_children_ids(self, node_id):
        hit = self.es_client.get(index="raptor", id=node_id)
        return hit["_source"]["children"]

    def filter_knn(self,
        query,
        query_embedding:list[float],
        top_k:int,
        level:int,
        node_ids:list[str]=None
    ):
        """knn搜索并指定layer"""
        knn = {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": top_k,
            "num_candidates": 10000,
            "filter": {
                "bool": {
                    "must": [
                        {"term": {"metadata.level": level}}
                    ],
                    "should": [
                        {"match": {"content": {"query": query}}}
                    ]
                }
            }
        }
        if node_ids:
            # 当遍历到中间层时，需要指定节点，否则使用的就是该层的所有节点
            # 这里要用的是DFS，而不是BFS
            knn["filter"]["bool"]["must"].append({"terms": {"chunk_id": node_ids}})

        resp = self.es_client.search(index="raptor", knn=knn, size=top_k)
        return resp["took"], resp["hits"]["hits"]

    def retrieve(self, query, top_k=10, levels=3):
        query = f"Given a search query, retrieve relevant passages that answer the query。\n\n{query}"
        query_embed = self.embedding_client.encode(query)

        candidates = []

        node_ids = None
        for level in range(1, levels + 1):
            elapsed, hits = self.filter_knn(
                query=query,
                query_embedding=query_embed,
                top_k=top_k,
                level=level,
                node_ids=node_ids
            )
            children_ids = []
            for hit in hits:
                source = hit["_source"]
                source["score"] = hit["_score"]
                candidates.append(source)
                # 获取当前节点的子节点
                curr_node_id = hit["_id"] or source.get("chunk_id")
                children_ids.extend(self.get_children_ids(curr_node_id))

            if len(children_ids) < 1:
                # 没有子节点，提前结束搜索
                break

            node_ids = children_ids
        return candidates


class CompressTreeRetriever:
    """将Tree压缩成一维的array，直接使用es搜索即可"""
    def __init__(self, embedding_client, es_client: Elasticsearch):
        self.embedding_client = embedding_client
        self.es_client = es_client

    def retrieve(self, query, top_k=10):
        query = f"Given a search query, retrieve relevant passages that answer the query。\n\n{query}"
        query_embed = self.embedding_client.encode(query)

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000,
            "filter": {
                "bool": {
                    "should": [
                        {"match": {"content": {"query": query}}},
                    ]
                }
            }
        }

        resp = self.es_client.search(index="raptor", knn=knn, size=top_k)

        elapsed, hits = resp["took"], resp["hits"]["hits"]

        candidates = []
        for hit in hits:
            source = hit["_source"]
            source["score"] = hit["_score"]
            candidates.append(source)

        return candidates


if __name__ == '__main__':
    from src.index import VllmEmbedding
    embedding_client = VllmEmbedding(
        url="http://192.168.10.187:5002/v1/embeddings",
        model="Qwen3-Embedding-0.6B"
    )
    es_client = Elasticsearch("http://elastic:+ZWNahlRPSAwNj2g5Upr@192.168.10.187:9200")

    retriever = TreeRetriever(embedding_client, es_client)

    query = "FswNetInit 是干嘛的"

    candidates = retriever.retrieve(query, levels=10)

    for cand in candidates:
        print(cand["metadata"])