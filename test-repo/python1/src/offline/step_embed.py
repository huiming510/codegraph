# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/21
# @Author  : cuils
# @Description: 
"""
import json
import math
from tqdm import tqdm
from src.index.embed import VllmEmbedding

client = VllmEmbedding(url="http://192.168.10.187:5002/v1/embeddings", model="Qwen3-Embedding-0.6B")

tofile = "../../examples/outputs/chunks_with_embedding.json"

items = []
with open("../../examples/outputs/chunks.json", encoding="utf8") as f:
    items += [json.loads(line.strip()) for line in f]
# with open("../data/batch-1/word_filter_and_dedup_chunks.json", encoding="utf8") as f:
#     items += [json.loads(line.strip()) for line in f]

batch_size = 16
start_index = 0
tbar = tqdm(total=math.ceil(len(items) / batch_size), desc="Embed")

with open(tofile, "w", encoding="utf8") as f:
    while start_index < len(items):
        batch = items[start_index:start_index + batch_size]

        texts = []
        for item in batch:
            content = item["content"]
            if item["metadata"] and "sheet_name" in item["metadata"]:
                content = f"file name: {item['metadata']['file_name'].split('.')[0]}\nsheet name: {item['metadata']['sheet_name']}\nbody:\n {content}"
            else:
                content = f"file name: {item['metadata']['file_name'].split('.')[0]}\nbody:\n {content}"
            texts.append(content)

        try:
            embeddings = client.batch_encode(texts)
        except Exception as e:
            start_index += batch_size
            tbar.update(1)
            continue

        for item, embedding in zip(batch, embeddings):
            item["embedding"] = embedding
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

        start_index += batch_size
        tbar.update(1)