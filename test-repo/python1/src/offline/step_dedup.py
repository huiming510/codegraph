# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/24
# @Author  : cuils
# @Description: 
"""
import re
import json
from unicodedata import normalize


def filter_chunk(content):
    content = normalize("NFKC", content)
    content = re.sub(r"[!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~\s。，？“”‘；：·’！￥…（）【】、《》]", "", content)

    return content


def main():
    dedup = set()
    cnt = 0
    dedup_items = []
    for i in range(4):
        with open(f"../data/outputs/word_chunks_{i + 1}.json", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line.strip())
                content = filter_chunk(item['content'])
                cnt += 1
                if len(content) < 100 or content in dedup:
                    continue

                dedup.add(content)
                item["content"] = normalize("NFKC", item["content"])
                dedup_items.append(item)

    print(cnt, len(dedup_items))
    with open(f"../data/outputs/word_filter_and_dedup_chunks.json", "w", encoding="utf-8") as f:
        for item in dedup_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == '__main__':
    main()
