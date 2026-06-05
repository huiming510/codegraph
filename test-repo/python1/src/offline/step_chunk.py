# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/17
# @Author  : cuils
# @Description:
"""
import uuid
import json
from multiprocessing import Pool
from tqdm import tqdm
from transformers import AutoTokenizer

from src.preprocess.base import Chunk
from src.preprocess.chunk import MarkdownTextSplitter


def run(args):
    fromfile, savefile, index = args
    tokenizer = AutoTokenizer.from_pretrained("../models/BAAI/bge-m3", use_fast=True)
    text_splitter = MarkdownTextSplitter.from_huggingface_tokenizer(
        tokenizer=tokenizer,
        chunk_size=1024,
        chunk_overlap=256
    )
    tbar = tqdm(total=300000, desc=f"Process-{index}")
    cnt = 0
    with open(fromfile, encoding="utf8") as fin, open(savefile, "w", encoding="utf-8") as fout:
        for _line in fin:
            item = json.loads(_line.strip())

            content = item["content"]
            # markdown 有图片，太长， 将图片抽出来， 再处理
            lines = []
            for line in content.splitlines():
                if not lines and not line.strip():
                    continue
                if "(data:image" in line.strip()[:100]:
                    continue
                lines.append(line)

            segments = text_splitter.split_text("\n".join(lines))

            for seg in segments:
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=item["doc_id"],
                    content=seg,
                    metadata=item["metadata"]
                )

                fout.write(chunk.model_dump_json() + "\n")

                cnt += 1
            tbar.update(1)
    print(cnt)


if __name__ == '__main__':
    mapping = [
        ["../data/batch-1/word_documents_1.json", "../data/batch-1/word_chunks_1.json", 1],
        ["../data/batch-1/word_documents_2.json", "../data/batch-1/word_chunks_2.json", 2],
        ["../data/batch-1/word_documents_3.json", "../data/batch-1/word_chunks_3.json", 3],
        ["../data/batch-1/word_documents_4.json", "../data/batch-1/word_chunks_4.json", 4],
    ]

    num_processes = len(mapping)

    pool = Pool(processes=num_processes)

    pool.map(func=run, iterable=mapping)

    pool.close()
    pool.join()
