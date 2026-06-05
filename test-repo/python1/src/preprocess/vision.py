# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/6 17:45
# @Author  : cuils
# @Description: ocr 识别 文档中的图片内容
"""
import os
import uuid
import json
import base64
import openai
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from io import BytesIO

from format_convert import LibreofficeFormatConverter, BaseFormatConverter


FIGURE_DESCRIBE_PROMPT = """
## ROLE
You are an expert visual data analyst.

## GOAL
Analyze the image and provide a comprehensive description of its content. Focus on identifying the type of visual data representation (e.g., bar chart, pie chart, line graph, table, flowchart), its structure, and any text captions or labels included in the image.

## TASKS
1. Describe the overall structure of the visual representation. Specify if it is a chart, graph, table, or diagram.
2. Identify and extract any axes, legends, titles, or labels present in the image. Provide the exact text where available.
3. Extract the data points from the visual elements (e.g., bar heights, line graph coordinates, pie chart segments, table rows and columns).
4. Analyze and explain any trends, comparisons, or patterns shown in the data.
5. Capture any annotations, captions, or footnotes, and explain their relevance to the image.
6. Only include details that are explicitly present in the image. If an element (e.g., axis, legend, or caption) does not exist or is not visible, do not mention it.
7. Return in Japanese.

## OUTPUT FORMAT (Include only sections relevant to the image content)
- Description: [Image description]
- Title: [Title text, if available]
- Axes / Legends / Labels: [Details, if available]
- Data Points: [Extracted data]
- Trends / Insights: [Analysis and interpretation]
- Captions / Annotations: [Text and relevance, if available]

> Ensure high accuracy, clarity, and completeness in your analysis, and include only the information present in the image. Avoid unnecessary statements about missing elements.
"""


class VisionSummary:
    def __init__(self, base_url, api_key="EMPTY", model=None, converter:BaseFormatConverter=None):
        self.converter = converter
        if self.converter is None:
            self.converter = LibreofficeFormatConverter()

        self.client = openai.Client(base_url=base_url, api_key=api_key)
        self.model = model

    def llm(self, img_ext, img_str):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": FIGURE_DESCRIBE_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{img_ext};base64,{img_str}"
                        }
                    }
                ]
            }
        ]
        try:
            resp = self.client.chat.completions.create(messages=messages, model=self.model)
            return resp.choices[0].message.content
        except Exception as e:
            print(repr(e))
        return None

    def run(self, img_name, img_ext, img_str):
        # 判断是否要进行格式转换
        if img_ext.lower() not in ["png", "jpg", "jpeg", "gif", "bmp"]:
            cache_dir = self.converter.cache_dir
            origin_path = os.path.join(cache_dir, f"{uuid.uuid4()}_{img_name}") # 多线程下防止出现同名文件覆盖问题
            with open(origin_path, "wb") as f:
                f.write(base64.b64decode(img_str))
            try:
                new_path = self.converter.convert(
                    input_filepath=origin_path,
                    input_format=img_ext.lower(),
                    output_format="png",
                    output_suffix="png"
                )
            except Exception as e:
                print(repr(e))
                return None

            with open(new_path, "rb") as f:
                img_byte = f.read()
            img_str = base64.b64encode(img_byte).decode()
            img_ext = "png"

        desc = self.llm(img_ext, img_str)

        return desc


def main():
    vision_summary = VisionSummary(
        base_url="http://172.27.99.3:8041/v1",
        model="Qwen3-VL-30B-A3B-Instruct"
    )

    frompath = "../../data/Toshiba/word_documents_v20260119.json"
    savepath = "../../data/Toshiba/word_documents_v20260119_with_vision.json"

    with open(frompath, encoding="utf-8") as f:
        items = [json.loads(line.strip()) for line in f]

    with open(savepath, "w", encoding="utf-8") as f:
        for item in tqdm(items, desc="Vision"):
            content = item["content"]
            images = item["images"]

            futures = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                for image in images:
                    future = executor.submit(vision_summary.run, image["img_name"], image["img_ext"], image["img_str"])
                    futures.append(future)
            descriptions = [future.result() for future in futures]

            for image, desc in zip(images, descriptions):
                image["description"] = desc
                if desc is not None:
                    content = content.replace(f"![media/image]({image['img_name']})", f"![media/image]({image['img_name']} {desc})")

            item["content"] = content
            f.write(json.dumps(item, ensure_ascii=False)+"\n")




if __name__ == '__main__':
    # main()

    # with open("../../data/Toshiba/word_documents_v20260119_with_vision.json", "r", encoding="utf-8") as f:
    #     items = [json.loads(line.strip()) for line in f]
    #
    # for item in items[3:]:
    #     if item["images"]:
    #         print(item["content"])
    #         exit(0)

    with open("E:/東芝流通・小売り業務知識/2_飲食教育/FSCompass/01.仕様書/00.標準/29.標準V40/02_全て/機能仕様書/正式50版(V40.0)_20240315/０１．登録/画面/01.01.01.01.bmp", "rb") as f:
        _byte = f.read()

    img_str = base64.b64encode(_byte).decode()

    vision_summary = VisionSummary(
        base_url="http://172.27.99.3:8041/v1",
        model="Qwen3-VL-30B-A3B-Instruct"
    )

    desc = vision_summary.run(img_name="temp.bmp", img_ext="bmp", img_str=img_str)

    print(desc)