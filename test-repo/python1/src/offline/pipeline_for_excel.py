# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/10 10:16
# @Author  : cuils
# @Description: 数据流程
1. 获取所有文件绝对路径
2. 读取、解析文件到json, 并保存为json格式
3. 进行chunk分块
4. embedding计算
5. 保存
"""

import os
import logging
import warnings
from tqdm import tqdm
from pathlib import Path
from src.preprocess.doc_parser import ExcelParser


warnings.filterwarnings(action="ignore")


def load_files():
    with open("../data/inputs/filenames_2.txt", encoding="utf8") as f:
        filenames = f.readlines()

    return filenames


def pipeline():
    log_file = f"../logs/log_excel_parser.log"

    handler = logging.FileHandler(log_file, encoding="utf8", mode="w")
    formatter = logging.Formatter('[%(levelname)s %(filename)s:%(lineno)s]:%(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger("parser")

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    parser = ExcelParser(logger=logger)
    
    filenames = load_files()

    filter_filenames = []

    for filepath in filenames:
        filepath = Path(filepath.strip())
        if not os.path.exists(filepath):
            print(f"[ERROR]: `{filepath}` 文件不存在")
            continue

        if filepath.suffix not in parser.support_file_formats:
            continue
        filter_filenames.append(filepath)


    with open(r"../data/batch-2/excel_documents.json", "w", encoding="utf8") as f:

        for filepath in tqdm(filter_filenames):

            documents = parser.parse(filepath)

            for document in documents:
                # document.metadata.update(item)

                f.write(document.model_dump_json()+"\n")



if __name__ == '__main__':

    pipeline()