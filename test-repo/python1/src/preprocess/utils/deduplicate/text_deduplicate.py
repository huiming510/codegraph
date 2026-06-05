# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 10:56
# @Author  : fubin
# @Description:
"""
import math
from collections import Counter, defaultdict


def simhash_deduplicate(texts: list[str], hamming_max: int = 3, bucket_bits: int = 16) -> list[int]:
    """simhash 文本去重"""
    buckets = defaultdict(list)
    keep_indices = []
    for idx, text in enumerate(texts):
        # 64bit 无符号哈希（Python 自带 hash）
        h = hash(text) & ((1 << 64) - 1)
        # 前 bucket_bits 位作为桶号
        bucket = h >> (64 - bucket_bits)
        # 桶内两两比对
        for _, exist_hash in buckets[bucket]:
            if bin(h ^ exist_hash).count('1') <= hamming_max:
                break  # 重复，跳过
        else:
            buckets[bucket].append((idx, h))
            keep_indices.append(idx)
    return keep_indices


def tfidf_cosine_deduplicate(texts: list[str], threshold: float = 0.90) -> list[int]:
    """tfidf 余弦相似度去重，
    Note：tfidf需要分词和去除停用词，这里没有分词
    """
    tfs = [Counter(t) for t in texts]
    vocab = set().union(*[t.keys() for t in tfs])
    idf = {ch: math.log(len(texts) / (sum(1 for t in tfs if ch in t) + 1)) for ch in vocab}

    # 2. 余弦比对（分桶优化：前 16 bit 签名）
    signature = lambda tf_dict: hash(tuple(sorted(tf_dict.items()))) >> 48
    buckets = defaultdict(list)
    keep_indices = []
    for idx, tf_dict in enumerate(tfs):
        sig = signature(tf_dict)
        vec1 = [tf_dict.get(ch, 0) * idf[ch] for ch in vocab]
        norm1 = math.sqrt(sum(v * v for v in vec1))
        # 桶内比对
        for _, exist_sig, exist_vec, exist_norm in buckets[sig]:
            if exist_sig == sig:  # 签名相同才比对
                vec2 = exist_vec
                norm2 = exist_norm
                dot = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
                cosine = dot / (norm1 * norm2) if norm1 and norm2 else 0.0
                if cosine >= threshold:
                    break
        else:
            buckets[sig].append((idx, sig, vec1, norm1))
            keep_indices.append(idx)
    return keep_indices