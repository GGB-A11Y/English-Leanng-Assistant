"""阅读理解:AI 生成文章 + 题目,提交判分零 LLM 成本(契约 3.6)。

重要设计约定:正确答案与逐题解析在生成时一并产出并落库,
提交接口直接判分,不再调用 LLM。

学段分类:小学/初中/高中 → 映射到 CEFR 难度带(带内随机,增加变化):
  小学 → A1~A2;初中 → A2~B1;高中 → B1~B2
"""
import random
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..llm import generate_structured
from ..models import ReadingArticle, User
from ..prompts import ARTICLE_SYSTEM
from ..schemas import (
    ArticleGenerateIn, ArticleLlm, ArticleOut, ArticleSubmitIn, ArticleSubmitOut,
)

router = APIRouter(tags=["reading"])

# 学段 → (中文名, CEFR 难度带)
STAGE_BANDS = {
    "primary": ("小学", ["A1", "A2"]),
    "junior": ("初中", ["A2", "B1"]),
    "senior": ("高中", ["B1", "B2"]),
}


def _resolve_stage_level(payload: ArticleGenerateIn) -> tuple[str, str]:
    """返回 (stage, level):stage 优先,映射到难度带内随机 CEFR 等级。"""
    if payload.stage:
        band = STAGE_BANDS.get(payload.stage)
        if not band:
            raise HTTPException(422, "无效的学段")
        return payload.stage, random.choice(band[1])
    return "", payload.level or "B1"


def _normalize_question(q) -> dict | None:
    """校验 LLM 生成的题目是否符合契约,返回规范化后的题目(含答案与解析)。"""
    if q.type == "single_choice":
        if len(q.options) != 4 or not q.correct_answer or q.correct_answer not in q.options:
            return None
        return {
            "type": q.type,
            "question": q.question,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
        }
    # true_false:契约要求 options 恰为 ["true", "false"],answer 为小写字符串
    options = [str(o).strip().lower() for o in q.options]
    answer = q.correct_answer.strip().lower()
    if options != ["true", "false"] or answer not in ("true", "false"):
        return None
    return {
        "type": q.type,
        "question": q.question,
        "options": ["true", "false"],
        "correct_answer": answer,
        "explanation": q.explanation,
    }


@router.post("/reading/articles/generate", response_model=ArticleOut)
def generate_article(
    payload: ArticleGenerateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(payload.topic) > 100:
        raise HTTPException(422, "主题过长(最多 100 字符)")
    stage, level = _resolve_stage_level(payload)
    topic_hint = (
        f"文章主题:{payload.topic.strip()}" if payload.topic.strip() else "主题不限,选一个适合该难度的话题"
    )
    prompt_user = f"CEFR 难度:{level}\n{topic_hint}"

    # 生成 + 语义校验,不合法则重试一次;整体受时间预算约束(前端超时 120s)
    deadline = time.monotonic() + 100.0
    result: ArticleLlm | None = None
    for _ in range(2):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        result = generate_structured(ArticleLlm, ARTICLE_SYSTEM, prompt_user, attempts=2, budget=min(60.0, remaining))
        if 1 <= len(result.questions) <= 10 and all(_normalize_question(q) for q in result.questions):
            break
        result = None
    if result is None:
        raise HTTPException(502, "生成失败,请重试")

    questions = [
        {"id": f"q_{i}", **_normalize_question(q)}
        for i, q in enumerate(result.questions, start=1)
    ]
    article = ReadingArticle(
        user_id=user.id,
        title=result.title,
        level=level,
        stage=stage,
        content=result.content,
        word_count=len(result.content.split()),  # 词数由服务端计算,不信任 LLM
        questions=questions,
        vocabulary_notes=[v.model_dump() for v in result.vocabulary_notes],
    )
    db.add(article)
    db.commit()
    return ArticleOut(
        article_id=article.article_id,
        title=article.title,
        level=article.level,
        stage=article.stage,
        content=article.content,
        word_count=article.word_count,
        # 不下发 correct_answer/explanation(契约:正确答案仅服务端存储)
        questions=[
            {"id": q["id"], "type": q["type"], "question": q["question"], "options": q["options"]}
            for q in questions
        ],
        vocabulary_notes=article.vocabulary_notes,
    )


@router.post("/reading/articles/{article_id}/submit", response_model=ArticleSubmitOut)
def submit_article(
    article_id: str,
    payload: ArticleSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = db.get(ReadingArticle, article_id)
    if not article or article.user_id != user.id:
        raise HTTPException(404, "文章不存在")

    answer_map = {str(a.get("question_id")): a.get("answer") for a in payload.answers}
    results, score = [], 0
    for q in article.questions:
        your = answer_map.get(q["id"])  # 未作答的题可不传,判为错误
        correct = your == q["correct_answer"]
        if correct:
            score += 1
        results.append(
            {
                "question_id": q["id"],
                "correct": correct,
                "your_answer": your,
                "correct_answer": q["correct_answer"],
                "explanation": q.get("explanation", ""),
            }
        )
    return ArticleSubmitOut(score=score, total=len(article.questions), results=results)
