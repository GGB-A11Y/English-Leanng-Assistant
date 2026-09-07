"""内置词库(小学 / 初中 / 高中必备词汇)。

数据来源:KyleBing/english-vocabulary(github.com/KyleBing/english-vocabulary,
个人学习用途),经 tools/convert_wordlists.py 转换为紧凑 JSON。
词条自带音标/中文释义/英文释义/例句/搭配/同近义词,**导入零 LLM 成本**。
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "wordlists")

STAGES = [
    {"stage": "primary", "label": "小学必备", "desc": "人教版小学 3~6 年级词汇", "file": "primary.json"},
    {"stage": "junior", "label": "初中必备", "desc": "中考核心词汇", "file": "junior.json"},
    {"stage": "senior", "label": "高中必备", "desc": "高考 3500 词汇", "file": "senior.json"},
]


def get_stage(stage: str) -> dict | None:
    return next((s for s in STAGES if s["stage"] == stage), None)


def load_stage(stage: str) -> list[dict]:
    """读取某学段的词表(未找到返回空列表)。"""
    info = get_stage(stage)
    if not info:
        return []
    path = os.path.join(DATA_DIR, info["file"])
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
