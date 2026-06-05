# -*- coding: utf-8 -*-
"""
# @Time    : 2025/12/10 14:58
# @Author  : cuils
# @Description:
第一步：切块，计算向量，等同于 NaiveRAG
第二步：分组聚类 + LLM总结，产生新的chunk
第三步：重复执行第二步，直到文本不可再分，即总chunks为1
"""
import uuid
import json
import openai
import numpy as np
from umap import UMAP
from tqdm import tqdm
from sklearn.mixture import GaussianMixture
from concurrent.futures import ThreadPoolExecutor

from src.index import VllmEmbedding
from src.llm import OpenAIModel

# Tree结构定义
class Node:
    """树节点定义"""

    def __init__(self,
        chunk_id: str,
        doc_id: str | None,
        content: str,
        children: list[str | int],
        embedding: list[float],
        metadata: dict = None
    ) -> None:
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.content = content
        self.children = children
        self.embedding = embedding
        self.metadata = metadata
        self.leaf = len(self.children) == 0  # 叶子节点无子节点


embed_client = VllmEmbedding(
    url="http://192.168.10.187:5002/v1/embeddings",
    model="Qwen3-Embedding-0.6B"
)

llm = OpenAIModel(
    base_url="http://192.168.10.187:5004/v1",
    model="Qwen3-30B-A3B-Instruct-2507",
    thinking=False
)


def run_cluster(embeddings: np.ndarray):
    """聚类，默认最大聚类中心数量为 数据量的平方根，降维后的维度大小为10"""
    # 降维，防止出现维度灾难
    n_neighbors = min(max(int(len(embeddings) ** 0.5), 5), 50)  # 邻居数量，经验值是 5-50
    reduction_dim = min(10, len(embeddings) - 2)  # 降维后维度 经验值 10-50 当该值大于样本数量时，会报错。当k>N时，N*N不可能存在K个特征值
    reduced_embeddings = UMAP(
        n_neighbors=n_neighbors,
        n_components=reduction_dim,
        metric="cosine"
    ).fit_transform(embeddings)  # [N, 10]

    # 找到最优的聚类中心数量
    max_cluster_num = max(1, int(len(embeddings) ** 0.5))  # 最大聚类数量
    bics = []
    for n in tqdm(range(1, max_cluster_num + 1), desc="计算最优聚类中心数量"):
        gm = GaussianMixture(n_components=n, random_state=20251211)
        gm.fit(reduced_embeddings)
        bics.append(gm.bic(reduced_embeddings))

    optimal_cluster_num = np.argmin(bics)  # 最优聚类数量

    # GMM聚类
    gm = GaussianMixture(n_components=optimal_cluster_num, random_state=20251211).fit(reduced_embeddings)
    labels = gm.predict(reduced_embeddings)  # 每条数据被聚类到其中一个簇
    clusters = {k: np.where(labels == k)[0] for k in range(optimal_cluster_num)}
    return optimal_cluster_num, clusters


def summarize(context):
    messages = [
        {
            "role": "user",
            "content": f"Write a SUMMARY of the following, including as many key details as possible. Requirements：\nreturned language MUST be the same as the input language and no explanation is required。\n\n{context}"
        }
    ]
    result = llm(messages=messages, max_completion_tokens=4096)
    return result


def recursive_summarize(cluster_contents):
    """如果需要总结的内容超过阈值，则分步总结，直到最后仅包含1个内容
    """
    if len(cluster_contents) == 1:
        return cluster_contents[0]

    contexts = []
    curr_tokens_count, candidates = 0, []
    for content in cluster_contents:
        tokens_count = llm.get_tokens_count(prompt=content)
        curr_tokens_count += tokens_count
        if curr_tokens_count > 128000:  # 128k
            contexts.append("\n\n".join(candidates))
            curr_tokens_count, candidates = tokens_count, []
        candidates.append(content)

    if candidates:
        contexts.append("\n\n".join(candidates))
        candidates = []

    futures = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for context in contexts:
            futures.append(executor.submit(summarize, context))
        executor.shutdown(wait=True)

    new_contents = [f.result() for f in futures]
    return recursive_summarize(new_contents)


def build_tree(nodes: list[Node], max_levels=None, min_nodes=5, levels=[]):
    """
    构建树，这里返回的是树的层序遍历结果
    """
    # 递归终止条件，若当前需要聚类的节点数量小于阈值，终止
    if len(nodes) <= min_nodes or len(levels) == max_levels:
        return
    embeddings = np.asarray([node.embedding for node in nodes])  # [N, 1024]
    optimal_cluster_num, clusters = run_cluster(embeddings)

    print(f"当前倒数第{len(levels)}层，共{len(nodes)}个节点，最优聚类中心数量: {optimal_cluster_num}")

    # 这里要控制上下文的token数量，防止因超长导致中断

    summaries = []
    for cluster_id in range(optimal_cluster_num):
        cluster_indices = clusters[cluster_id]
        cluster_contents = [nodes[index].content for index in cluster_indices]
        summarization = recursive_summarize(cluster_contents)
        summaries.append([cluster_id, summarization])

    curr_level_nodes = []
    for _id, summarization in summaries:
        node = Node(
            chunk_id=str(uuid.uuid4()),
            doc_id=None,
            content=summarization,
            children=clusters[_id].tolist(),
            embedding=embed_client.encode(summarization)
        )
        curr_level_nodes.append(node)

    levels.append(curr_level_nodes)

    build_tree(curr_level_nodes, max_levels=max_levels, min_nodes=min_nodes, levels=levels)


def main():
    nodes = []
    with open("../../examples/outputs/chunks_with_embedding.json", encoding="utf8") as f:
        for line in f:
            item = json.loads(line.strip())
            node = Node(
                chunk_id=item["chunk_id"] or str(uuid.uuid4()),
                doc_id=None,
                content=item["content"],
                children=[],
                embedding=item["embedding"],
                metadata=item["metadata"]
            )
            nodes.append(node)

    levels = [nodes, ]

    build_tree(nodes, levels=levels)

    print(len(levels))

    for i in range(len(levels) - 1, 0, -1):
        level_nodes = levels[i]
        for node in level_nodes:
            child_indices = node.children
            child_uids = []
            for index in child_indices:
                child_uids.append(levels[i - 1][index].chunk_id)
            node.children = child_uids

    with open("../../examples/outputs/raptor_chunks_with_embedding.json", "w", encoding="utf8") as f:
        for i, level in enumerate(levels[::-1]):
            for node in level:
                metadata = node.metadata or {}
                metadata.update({"level": i + 1})
                _item = {
                    "chunk_id": node.chunk_id,
                    "doc_id": node.doc_id,
                    "content": node.content,
                    "children": node.children,
                    "embedding": node.embedding,
                    "metadata": metadata
                }
                f.write(json.dumps(_item, ensure_ascii=False) + "\n")


if __name__ == '__main__':
    main()
