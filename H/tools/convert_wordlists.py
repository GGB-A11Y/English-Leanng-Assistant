"""一次性工具:把 KyleBing/english-vocabulary 的 jsonl 词库转换为内置紧凑词表。

数据源:https://github.com/KyleBing/english-vocabulary
  - 小学:人教小学三~六年级(full/正序)
  - 初中:初中.jsonl(full/正序)
  - 高中:高中.jsonl(full/正序)

用法:python tools/convert_wordlists.py
输出:app/data/wordlists/{primary,junior,senior}.json
"""
import json
import os

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "wordlists", "raw")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "wordlists")

STAGES = {
    "primary": ["人教小学三年级.jsonl", "人教小学四年级.jsonl", "人教小学五年级.jsonl", "人教小学六年级.jsonl"],
    "junior": ["初中.jsonl"],
    "senior": ["高中.jsonl"],
}


def parse_file(path: str, out: dict) -> int:
    """解析单行 JSON 词库文件,提取词条核心字段(去重:同词保留第一条)。"""
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            head = item.get("headWord")
            content = ((item.get("content") or {}).get("word") or {}).get("content") or {}
            if not head or not content:
                continue
            key = head.lower()
            if key in out:
                continue
            trans = content.get("trans") or []
            t = trans[0] if trans else {}
            sentences = ((content.get("sentence") or {}).get("sentences") or [])[:2]
            phrases = ((content.get("phrase") or {}).get("phrases") or [])[:6]
            synos = ((content.get("syno") or {}).get("synos") or [])
            antos = ((content.get("antos") or {}).get("anto") or [])
            synonyms = []
            for s in synos[:2]:
                for w in (s.get("hwds") or [])[:3]:
                    if w.get("w") and w["w"] not in synonyms and len(synonyms) < 5:
                        synonyms.append(w["w"])
            antonyms = [a.get("hwd") for a in antos if a.get("hwd")][:5]
            out[key] = {
                "word": head,
                "phonetic": content.get("phone") or content.get("usphone") or "",
                "pos": (t.get("pos") or "").strip(),
                "definition_cn": t.get("tranCn") or "",
                "definition_en": t.get("tranOther") or "",
                "examples": [
                    {"sentence": s.get("sContent", ""), "translation": s.get("sCn", "")}
                    for s in sentences
                    if s.get("sContent")
                ],
                "collocations": [
                    f"{p.get('pContent', '')}({p.get('pCn', '')})" if p.get("pCn") else p.get("pContent", "")
                    for p in phrases
                    if p.get("pContent")
                ],
                "synonyms": synonyms,
                "antonyms": antonyms,
            }
            count += 1
    return count


def main():
    for stage, files in STAGES.items():
        entries = {}
        total = 0
        for name in files:
            path = os.path.join(RAW_DIR, name)
            if not os.path.exists(path):
                print(f"  [跳过] 缺少原始文件: {name}")
                continue
            n = parse_file(path, entries)
            print(f"  {name}: {n} 行,累计去重后 {len(entries)} 词")
            total += n
        out_path = os.path.join(OUT_DIR, f"{stage}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(list(entries.values()), f, ensure_ascii=False)
        print(f"  -> 写出 {out_path}({len(entries)} 词)")


if __name__ == "__main__":
    main()
