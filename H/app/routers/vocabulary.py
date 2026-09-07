"""单词学习记忆:单词本 CRUD + AI 词条生成 + SM-2 复习 + 自测 + 内置词库导入(契约 3.3)。"""
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..builtin import STAGES, get_stage, load_stage
from ..database import get_db
from ..llm import generate_structured
from ..models import Quiz, User, Word, WordGroup
from ..prompts import WORD_ENTRY_SYSTEM
from ..schemas import (
    GroupCreateIn, QuizQuestionOut, QuizStartOut, QuizSubmitIn, QuizSubmitOut,
    ReviewItemOut, ReviewQueueOut, ReviewResultOut, ReviewSubmitIn,
    StageImportIn, WordCreateIn, WordEntryLlm, WordOut, WordPage, WordPatchIn, iso, word_to_out,
)
from ..sm2 import apply_sm2

router = APIRouter(tags=["vocabulary"])


def _get_word_or_404(word_id: str, user: User, db: Session) -> Word:
    """单词归属校验:不存在或不属于当前用户一律 404(不泄露存在性)。"""
    word = db.get(Word, word_id)
    if not word or word.user_id != user.id:
        raise HTTPException(404, "单词不存在")
    return word


def _user_words(db: Session, user: User) -> list[Word]:
    return db.query(Word).filter(Word.user_id == user.id).all()


def _generate_entry(word: str) -> WordEntryLlm:
    return generate_structured(WordEntryLlm, WORD_ENTRY_SYSTEM, f"单词:{word}")


def _fill_ai_fields(w: Word, entry: WordEntryLlm) -> None:
    """把 LLM 生成的 AI 字段写入词条(用户字段 tags/note 不在此列)。"""
    w.phonetic = entry.phonetic
    w.pos = entry.pos
    w.definition_cn = entry.definition_cn
    w.definition_en = entry.definition_en
    w.examples = [e.model_dump() for e in entry.examples]
    w.roots_affixes = [r.model_dump() for r in entry.roots_affixes]
    w.synonyms = entry.synonyms
    w.antonyms = entry.antonyms
    w.collocations = entry.collocations


@router.get("/vocabulary/builtin")
def list_builtin(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """内置词库学段列表(含当前用户已导入数量,用于导入/删除管理)。"""
    tag_counts: dict = {}
    for w in _user_words(db, user):
        for t in w.tags or []:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    return {
        "stages": [
            {
                "stage": s["stage"],
                "label": s["label"],
                "desc": s["desc"],
                "count": len(load_stage(s["stage"])),
                "imported": tag_counts.get(s["label"], 0),
            }
            for s in STAGES
        ]
    }


@router.delete("/vocabulary/builtin/{stage}")
def delete_stage(stage: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除当前用户已导入的某学段词库(按学段标签批量删除该学段全部单词)。"""
    info = get_stage(stage)
    if not info:
        raise HTTPException(404, "词库不存在")
    words = [w for w in _user_words(db, user) if info["label"] in (w.tags or [])]
    for w in words:
        db.delete(w)
    db.commit()
    return {"ok": True, "deleted": len(words), "label": info["label"]}


@router.post("/vocabulary/words/import")
def import_stage(
    payload: StageImportIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按学段批量导入内置词库(去重,词条数据来自词库本身,不调用 AI)。"""
    info = next((s for s in STAGES if s["stage"] == payload.stage), None)
    if not info:
        raise HTTPException(404, "词库不存在")
    entries = load_stage(payload.stage)
    if not entries:
        raise HTTPException(500, "词库数据缺失")

    existing = {w.word.lower() for w in _user_words(db, user)}
    new_words = []
    for e in entries:
        if e["word"].lower() in existing:
            continue
        existing.add(e["word"].lower())
        new_words.append(
            Word(
                user_id=user.id,
                word=e["word"],
                phonetic=e.get("phonetic") or "",
                pos=e.get("pos") or "",
                definition_cn=e.get("definition_cn") or "",
                definition_en=e.get("definition_en") or "",
                examples=e.get("examples") or [],
                roots_affixes=[],
                synonyms=e.get("synonyms") or [],
                antonyms=e.get("antonyms") or [],
                collocations=e.get("collocations") or [],
                tags=[info["label"]],
            )
        )
    db.add_all(new_words)
    db.commit()
    return {
        "stage": payload.stage,
        "label": info["label"],
        "imported": len(new_words),
        "skipped": len(entries) - len(new_words),
    }


@router.get("/vocabulary/words", response_model=WordPage)
def list_words(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    q: str | None = None,
    group: str | None = None,
    status: str | None = None,  # learned=复习过至少一次 | unlearned=从未复习
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Word).filter(Word.user_id == user.id)
    if q and q.strip():
        query = query.filter(Word.word.contains(q.strip()))
    if status == "learned":
        query = query.filter(Word.next_review_at.is_not(None))
    elif status == "unlearned":
        query = query.filter(Word.next_review_at.is_(None))
    all_words = query.order_by(Word.created_at.desc(), Word.id).all()
    if group and group.strip():
        # 按自定义分组筛选(分组存在词的 groups JSON 中,本地过滤)
        all_words = [w for w in all_words if group.strip() in (w.groups or [])]
    total = len(all_words)
    words = all_words[(page - 1) * page_size : (page - 1) * page_size + page_size]
    return WordPage(
        items=[word_to_out(w) for w in words], total=total, page=page, page_size=page_size
    )


@router.get("/vocabulary/groups")
def list_groups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户的分组列表(含每个分组下的单词数);空分组也保留(建组即持久化)。"""
    counts: dict = {}
    for w in _user_words(db, user):
        for g in w.groups or []:
            counts[g] = counts.get(g, 0) + 1
    stored = {
        g.name for g in db.query(WordGroup).filter(WordGroup.user_id == user.id).all()
    }
    names = sorted(set(counts) | stored)
    return {"groups": [{"name": n, "count": counts.get(n, 0)} for n in names]}


@router.post("/vocabulary/groups")
def create_group(payload: GroupCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name or len(name) > 20:
        raise HTTPException(422, "分组名不能为空且不超过 20 个字符")
    if db.query(WordGroup).filter(WordGroup.user_id == user.id, WordGroup.name == name).first():
        raise HTTPException(409, "分组已存在")
    db.add(WordGroup(user_id=user.id, name=name))
    db.commit()
    return {"name": name, "count": 0}


@router.delete("/vocabulary/groups/{name}")
def delete_group(name: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除分组:移除分组记录,并把所有单词从该分组中摘除(不删单词本身)。

    兼容详情页直接输入、无分组记录的「散装分组名」。
    """
    grp = db.query(WordGroup).filter(WordGroup.user_id == user.id, WordGroup.name == name).first()
    words = [w for w in _user_words(db, user) if name in (w.groups or [])]
    if not grp and not words:
        raise HTTPException(404, "分组不存在")
    for w in words:
        w.groups = [g for g in w.groups if g != name]
    if grp:
        db.delete(grp)
    db.commit()
    return {"ok": True, "removed_from": len(words)}


@router.post("/vocabulary/words", response_model=WordOut)
def add_word(payload: WordCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    word = payload.word.strip()
    if not word or len(word) > 64:
        raise HTTPException(422, "单词不能为空且长度不超过 64 个字符")
    exists = db.query(Word).filter(Word.user_id == user.id, Word.word.ilike(word)).first()
    if exists:
        raise HTTPException(409, "单词已存在")  # 契约:重复添加返回 409

    entry = _generate_entry(word)
    w = Word(
        user_id=user.id,
        word=word,
        tags=entry.tags,  # 标签随 AI 生成;用户可后续 PATCH 修改
    )
    _fill_ai_fields(w, entry)
    db.add(w)
    try:
        db.commit()
    except IntegrityError:  # 应用层检查之外的并发兜底:复合唯一索引 (user_id, word)
        db.rollback()
        raise HTTPException(409, "单词已存在")
    db.refresh(w)
    return word_to_out(w)


@router.get("/vocabulary/words/{word_id}", response_model=WordOut)
def get_word(word_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return word_to_out(_get_word_or_404(word_id, user, db))


@router.post("/vocabulary/words/{word_id}/generate", response_model=WordOut)
def regenerate_word(word_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w = _get_word_or_404(word_id, user, db)
    entry = _generate_entry(w.word)
    _fill_ai_fields(w, entry)
    # 保留学段标签(删除学段词库按标签识别,见 delete_stage):
    # AI 生成的 tags 不含学段标签,直接覆盖会导致该词在删除学段时漏删;
    # 反之 AI 误打学段标签也会被误删。学段标签保留原值,新标签合并在后。
    stage_labels = [s["label"] for s in STAGES]
    old_stage_tags = [t for t in (w.tags or []) if t in stage_labels]
    w.tags = old_stage_tags + [t for t in entry.tags if t not in old_stage_tags]
    db.commit()
    db.refresh(w)
    return word_to_out(w)


@router.patch("/vocabulary/words/{word_id}", response_model=WordOut)
def update_word(
    word_id: str,
    payload: WordPatchIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    w = _get_word_or_404(word_id, user, db)
    if payload.tags is not None:
        w.tags = payload.tags
    if payload.groups is not None:
        w.groups = payload.groups
    if payload.note is not None:
        if len(payload.note) > 500:
            raise HTTPException(422, "备注过长(最多 500 字符)")
        w.note = payload.note
    db.commit()
    db.refresh(w)
    return word_to_out(w)


@router.delete("/vocabulary/words/{word_id}")
def delete_word(word_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w = _get_word_or_404(word_id, user, db)
    db.delete(w)
    db.commit()
    return {"ok": True}


@router.get("/vocabulary/review/due", response_model=ReviewQueueOut)
def review_due(
    include_new: bool = True,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now()
    due = (
        db.query(Word)
        .filter(Word.user_id == user.id, Word.next_review_at.is_not(None), Word.next_review_at <= now)
        .order_by(Word.next_review_at)
        .all()
    )
    items = list(due)
    if include_new:  # 到期词不足时,补从未学过的词(familiarity=0)
        new_words = (
            db.query(Word)
            .filter(Word.user_id == user.id, Word.next_review_at.is_(None))
            .order_by(Word.created_at)
            .all()
        )
        items = items + new_words
    items = items[:limit]
    return ReviewQueueOut(
        items=[
            ReviewItemOut(
                id=w.id, word=w.word, phonetic=w.phonetic,
                definition_cn=w.definition_cn, familiarity=w.familiarity, repetition=w.repetition,
            )
            for w in items
        ],
        due_count=len(due),  # 真实到期总数,不受 limit 影响
        total_count=db.query(Word).filter(Word.user_id == user.id).count(),
    )


@router.post("/vocabulary/review/{word_id}", response_model=ReviewResultOut)
def submit_review(
    word_id: str,
    payload: ReviewSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    w = _get_word_or_404(word_id, user, db)
    apply_sm2(w, payload.quality)
    db.commit()
    return ReviewResultOut(
        id=w.id,
        familiarity=w.familiarity,
        repetition=w.repetition,
        ease_factor=w.ease_factor,
        interval_days=w.interval_days,
        next_review_at=iso(w.next_review_at),
        is_mastered=w.repetition >= 5,
    )


@router.get("/vocabulary/quiz", response_model=QuizStartOut)
def start_quiz(count: int = Query(10, ge=1, le=50), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    words = [w for w in _user_words(db, user) if w.definition_cn]
    if len(words) < 4:
        raise HTTPException(400, "单词本中的单词不足(至少需要 4 个),先添加一些单词吧")

    sample = random.sample(words, min(count, len(words)))
    questions, answers = [], []
    for w in sample:
        # 干扰项:从其他词的中文释义中抽最多 3 个不同的
        distractors = []
        for other in words:
            if other.id == w.id:
                continue
            if (
                other.definition_cn != w.definition_cn
                and other.definition_cn not in distractors
            ):
                distractors.append(other.definition_cn)
            if len(distractors) == 3:
                break
        # 全词库释义都相同(或只有这一个词)时此题没有意义,跳过
        if not distractors:
            continue
        random.shuffle(distractors)
        # 契约约定:「打乱后正确答案是 options[0]」,判分依据记录在 answers 中
        options = [w.definition_cn] + distractors
        questions.append({"word": w.word, "phonetic": w.phonetic, "options": options})
        answers.append({"word": w.word, "answer": w.definition_cn})

    if not questions:
        raise HTTPException(400, "单词本中的单词不足(至少需要 4 个),先添加一些单词吧")

    quiz = Quiz(user_id=user.id, questions=questions, answers=answers)
    db.add(quiz)
    db.commit()
    return QuizStartOut(quiz_id=quiz.quiz_id, questions=[QuizQuestionOut(**q) for q in questions])


@router.post("/vocabulary/quiz/{quiz_id}/submit", response_model=QuizSubmitOut)
def submit_quiz(
    quiz_id: str,
    payload: QuizSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != user.id:
        raise HTTPException(404, "自测不存在或已失效,请重新开始")

    key = {a["word"]: a["answer"] for a in quiz.answers}
    results, score = [], 0
    for q in quiz.questions:
        ans = next((a for a in payload.answers if a.get("word") == q["word"]), None)
        idx = ans.get("answer_index") if ans else None
        your = q["options"][idx] if isinstance(idx, int) and 0 <= idx < len(q["options"]) else None
        correct = your == key[q["word"]]
        if correct:
            score += 1
        results.append(
            {"word": q["word"], "correct": correct, "your_answer": your, "correct_answer": key[q["word"]]}
        )
    return QuizSubmitOut(score=score, total=len(quiz.questions), results=results)
