# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 11:27
# @Author  : cuils
# @Description:
使用 Microsoft 的 Presidio 实现数据脱敏
from: https://github.com/microsoft/presidio
"""
from presidio_anonymizer import OperatorConfig, AnonymizerEngine
from presidio_analyzer import Pattern, PatternRecognizer, AnalyzerEngine


# 支持的实体类型
SENSITIVE_REGEXPS = [
    {
        "Field": "JAPAN_PERSONAL_NUMBER",
        "RegExp": "\\d{12}",
        "Description": "個人番号",
        "Language": "ja",
        "Mask_Length": 4
    },
    {
        "Field": "JAPAN_ZAIryu_CARD",
        "RegExp": "[A-Z]\\d{12}",
        "Description": "在留カード",
        "Language": "ja",
        "Mask_Length": 4
    },
    {
        "Field": "JAPAN_BANK_ACCOUNT",
        "RegExp": "\\d{5}-\\d{6,7}-\\d{1}",
        "Description": "銀行口座",
        "Language": "ja",
        "Mask_Length": 6
    }
]


class Desensitizer:
    """文本脱敏"""
    def __init__(self):
        self.anonymizer = AnonymizerEngine()
        self.analyzer = AnalyzerEngine()
        self.operators = {}
        for regexp in SENSITIVE_REGEXPS:
            # 实体模式识别
            recognizer = PatternRecognizer(
                supported_entity=regexp["Field"],
                patterns=[
                    Pattern(
                        name=regexp["Field"],
                        regex=regexp["RegExp"],
                        score=0.8
                    )
                ],
                supported_language=regexp["Language"]
            ),
            self.analyzer.registry.add_recognizer(recognizer)

            # 该实体类型如果处理，一般是mask掉，用*代替
            operator = OperatorConfig(
                operator_name="mask",
                params={
                    "chars_to_mask": regexp['Mask_Length'],  # 必填
                    "masking_char": "*",
                    "from_end": True  # ✅ 官方参数名，大小写别改})
                }
            )
            self.operators[regexp["Field"]] = operator

    def desensitize(self, text:str, language:str="ja") -> str:
        analyzer_results = self.analyzer.analyze(text, language=language)

        anonymize_results = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=self.operators
        )
        return anonymize_results.text




