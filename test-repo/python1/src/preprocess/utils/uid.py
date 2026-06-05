# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 11:23
# @Author  : fubin
# @Description:
根据内容生成哈希ID，支持MD5和SHA256两种方法
"""
import uuid
import hashlib


def generate_uid(content: str, method: str = "md5") -> str:
    # MD5	128 bit (32 hex)  2^64 分之一	2004 已破 仅用于非安全场景
    # 若 内容极短（< 20 字节）或 日写入量 < 万级，MD5 也可接受。
    if method == "md5":
        hash_id = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
    # SHA256	256 bit (64 hex)	2^128 分之一	目前安全 推荐用于生产
    # 若 内容长度 > 几十 KB 或 日写入量 > 百万级，优先选 SHA256；
    elif method == "sha256":
        hash_id = hashlib.sha256(content.encode(), usedforsecurity=False).hexdigest()
    else:
        hash_id = str(uuid.uuid4())
    return hash_id