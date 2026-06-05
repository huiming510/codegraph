# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 11:05
# @Author  : fubin
# @Description:
"""
import math
import numpy as np
from collections import defaultdict


def simhash_deduplicate(
    embeddings: list[np.ndarray],
    threshold: float = 0.95,
    bucket_bits: int = 16
) -> list[int]:
    """simhash embedding 去重，这里是不是可以用LSH"""
    # 前 bucket_bits 位分桶（降低比对量）
    keep_indices = []
    buckets = defaultdict(list)  # key: 前 N bit 签名，value: [(idx, vec), ...]
    for idx, vec in enumerate(embeddings):
        signature = int(hash(tuple(vec)) >> (64 - bucket_bits))  # 前 N bit
        # 桶内比对
        for _, exist_vec in buckets[signature]:
            norm_x = np.linalg.norm(vec)
            if norm_x:
                vec_ = vec / norm_x
            norm_y = np.linalg.norm(exist_vec)
            if norm_y:
                exist_vec_ = exist_vec / norm_y
            cos_sim = float(np.dot(vec_, exist_vec_))  # 已归一化，直接点积
            if cos_sim >= threshold:
                break  # 重复，跳过
        else:
            buckets[signature].append((idx, vec))
            keep_indices.append(idx)
    return keep_indices