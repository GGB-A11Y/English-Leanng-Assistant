"""SM-2 间隔重复算法(契约见 docs/API.md 3.3 / 4)。

- EF 初始 2.5,下限 1.3;quality < 3 时 repetition 重置为 0
- 间隔:首次成功 1 天 → 第二次 6 天 → 之后 round(上次间隔 × EF)
- familiarity = 最近一次评分;is_mastered 约定为 repetition >= 5
"""
from datetime import datetime, timedelta


def apply_sm2(word, quality: int):
    ef = word.ease_factor or 2.5
    rep = word.repetition or 0
    interval = word.interval_days or 0

    # SM-2 标准 EF 增量每次复习都应用(含失败):ΔEF = 0.1 - (5-q)*(0.08 + (5-q)*0.02)
    # 失败时 EF 下降,连续遗忘的词复习节奏会收紧,而不是 EF 恒为 2.5 偏松
    ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

    if quality < 3:
        rep = 0
        interval = 1
    else:
        if rep == 0:
            interval = 1
        elif rep == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ef))
        rep += 1

    word.familiarity = quality
    word.repetition = rep
    word.ease_factor = round(ef, 2)
    word.interval_days = interval
    word.next_review_at = datetime.now() + timedelta(days=interval)
    return word
