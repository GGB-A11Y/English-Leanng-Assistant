"""作文学习:内置题库 + 自定义题目(手动/批量 AI 整理)+ AI 批改 + 按需生成范文(契约 3.5)。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..llm import generate_structured, generate_text
from ..models import TopicGroup, WritingTopic, gen_id
from ..prompts import ESSAY_GRADE_SYSTEM, ESSAY_SAMPLE_SYSTEM, TOPIC_PARSE_SYSTEM
from ..schemas import (
    EssayGradeIn, EssayGradeLlm, EssaySampleIn, GroupCreateIn, SampleOut,
    TopicCreateIn, TopicImportIn, TopicListLlm, TopicOut, TopicParseIn, TopicPatchIn, TopicsOut,
)
from ..seed_topics import LEVEL_TO_STAGE

router = APIRouter(tags=["writing"])

# 学段中文名(与前端 constants 对应)
STAGE_LABELS = {"primary": "小学", "junior": "初中", "senior": "高中"}

# 手动添加题目时,学段对应的代表 CEFR 等级(用于批改/范文的难度提示)
STAGE_REPR_LEVEL = {"primary": "A1", "junior": "B1", "senior": "B2"}


def _topic_out(t: WritingTopic) -> TopicOut:
    return TopicOut(
        id=t.id, title=t.title, level=t.level, stage=t.stage,
        prompt=t.prompt, keywords=t.keywords or [], groups=t.groups or [],
    )


def _topic_sort_key(t: WritingTopic):
    """内置题(t_1..t_15)按序号排,自定义题(随机 id)排在后面。

    不能直接按 id 字符串排序:字典序下 "t_10" 会排在 "t_7" 前面。
    """
    if t.id.startswith("t_") and t.id[2:].isdigit():
        return (0, int(t.id[2:]))
    return (1, t.id)


@router.get("/writing/topics", response_model=TopicsOut)
def list_topics(
    stage: str | None = None,
    level: str | None = None,
    group: str | None = None,
    db: Session = Depends(get_db),
):
    """题目列表:按学段(stage)/CEFR(level)/自定义分组(group)筛选,皆可省略返回全部。"""
    query = db.query(WritingTopic)
    if stage:
        query = query.filter(WritingTopic.stage == stage)
    if level:
        query = query.filter(WritingTopic.level == level)
    topics = sorted(query.all(), key=_topic_sort_key)
    if group and group.strip():
        topics = [t for t in topics if group.strip() in (t.groups or [])]
    return TopicsOut(topics=[_topic_out(t) for t in topics])


@router.get("/writing/groups")
def list_groups(db: Session = Depends(get_db)):
    """作文题目分组列表(含每组的题目数);空分组也保留。"""
    counts: dict = {}
    for t in db.query(WritingTopic).all():
        for g in t.groups or []:
            counts[g] = counts.get(g, 0) + 1
    stored = {g.name for g in db.query(TopicGroup).all()}
    names = sorted(set(counts) | stored)
    return {"groups": [{"name": n, "count": counts.get(n, 0)} for n in names]}


@router.post("/writing/groups")
def create_group(payload: GroupCreateIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name or len(name) > 20:
        raise HTTPException(422, "分组名不能为空且不超过 20 个字符")
    if db.query(TopicGroup).filter(TopicGroup.name == name).first():
        raise HTTPException(409, "分组已存在")
    db.add(TopicGroup(name=name))
    db.commit()
    return {"name": name, "count": 0}


@router.delete("/writing/groups/{name}")
def delete_group(name: str, db: Session = Depends(get_db)):
    """删除分组:移除分组记录,并把所有题目从该分组摘除(不删题目本身)。"""
    grp = db.query(TopicGroup).filter(TopicGroup.name == name).first()
    topics = [t for t in db.query(WritingTopic).all() if name in (t.groups or [])]
    if not grp and not topics:
        raise HTTPException(404, "分组不存在")
    for t in topics:
        t.groups = [g for g in t.groups if g != name]
    if grp:
        db.delete(grp)
    db.commit()
    return {"ok": True, "removed_from": len(topics)}


@router.patch("/writing/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: str, payload: TopicPatchIn, db: Session = Depends(get_db)):
    """更新题目自定义字段(当前支持分组)。"""
    t = db.get(WritingTopic, topic_id)
    if not t:
        raise HTTPException(404, "题目不存在")
    if payload.groups is not None:
        t.groups = payload.groups
    db.commit()
    return _topic_out(t)


@router.post("/writing/topics", response_model=TopicOut)
def create_topic(payload: TopicCreateIn, db: Session = Depends(get_db)):
    """手动添加自定义题目(学段映射代表 CEFR 等级)。"""
    title = payload.title.strip()
    if not title or not payload.prompt.strip():
        raise HTTPException(422, "题目与写作要求不能为空")
    if len(title) > 80:
        raise HTTPException(422, "题目过长(最多 80 字符)")
    if len(payload.prompt.strip()) > 2000:
        raise HTTPException(422, "写作要求过长(最多 2000 字符)")
    if db.query(WritingTopic).filter(WritingTopic.title == title).first():
        raise HTTPException(409, "题目已存在")
    t = WritingTopic(
        id=gen_id("t"),
        title=title,
        level=STAGE_REPR_LEVEL.get(payload.stage, "B1"),
        stage=payload.stage,
        prompt=payload.prompt.strip(),
        keywords=payload.keywords,
    )
    db.add(t)
    db.commit()
    return _topic_out(t)


@router.post("/writing/topics/parse", response_model=TopicListLlm)
def parse_topics(payload: TopicParseIn):
    """批量导入第一步:AI 把粘贴的题目素材整理成规范题目(预览用,不入库)。"""
    if not payload.text.strip():
        raise HTTPException(422, "题目素材不能为空")
    if len(payload.text) > 10000:
        raise HTTPException(422, "题目素材过长(最多 10000 字符)")
    return generate_structured(TopicListLlm, TOPIC_PARSE_SYSTEM, f"题目素材:\n{payload.text}")


@router.post("/writing/topics/import")
def import_topics(payload: TopicImportIn, db: Session = Depends(get_db)):
    """批量导入第二步:把 AI 整理好的题目入库(按标题去重)。"""
    existing = {t.title for t in db.query(WritingTopic).all()}
    imported = 0
    for item in payload.topics:
        title = item.title.strip()
        prompt = (item.prompt or "").strip()
        # 与 create_topic 校验口径一致:写作要求为空(前端「写作」步没有内容)的题目无意义
        if not title or not prompt or title in existing:
            continue
        existing.add(title)
        db.add(
            WritingTopic(
                id=gen_id("t"),
                title=title,
                level=item.level,
                stage=LEVEL_TO_STAGE.get(item.level, ""),
                prompt=prompt,
                keywords=item.keywords,
            )
        )
        imported += 1
    db.commit()
    return {"imported": imported, "skipped": len(payload.topics) - imported}


@router.delete("/writing/topics/{topic_id}")
def delete_topic(topic_id: str, db: Session = Depends(get_db)):
    t = db.get(WritingTopic, topic_id)
    if not t:
        raise HTTPException(404, "题目不存在")
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.post("/writing/essays/grade", response_model=EssayGradeLlm)
def grade_essay(payload: EssayGradeIn, db: Session = Depends(get_db)):
    if not payload.content.strip():
        raise HTTPException(422, "作文内容不能为空")
    if len(payload.content) > 8000:
        raise HTTPException(422, "作文内容过长(最多 8000 字符)")
    if len(payload.title) > 200:
        raise HTTPException(422, "作文标题过长(最多 200 字符)")
    if len(payload.requirement) > 500:
        raise HTTPException(422, "批改要求过长(最多 500 字符)")

    topic = None
    if payload.topic_id:
        topic = db.get(WritingTopic, payload.topic_id)
        if not topic:
            raise HTTPException(404, "题目不存在")

    parts = []
    if topic:
        parts.append(f"作文题目:{topic.title}(CEFR {topic.level})\n题目要求:{topic.prompt}")
        if topic.keywords:
            parts.append(f"建议覆盖的关键词:{', '.join(topic.keywords)}")
    if payload.stage:
        # 评分参照学生学段:小学生按小学标准宽容打分,高中生按高中标准从严
        label = STAGE_LABELS.get(payload.stage, payload.stage)
        parts.append(f"学生学段:{label},评分与评语请参照该学段的课程标准")
    if payload.title.strip():
        parts.append(f"学生作文标题:{payload.title.strip()}")
    parts.append(f"学生作文:\n{payload.content}")
    if payload.requirement.strip():
        parts.append(f"学生附加的批改要求:{payload.requirement.strip()}")
    return generate_structured(EssayGradeLlm, ESSAY_GRADE_SYSTEM, "\n\n".join(parts))


@router.post("/writing/essays/sample", response_model=SampleOut)
def generate_sample(payload: EssaySampleIn, db: Session = Depends(get_db)):
    topic = db.get(WritingTopic, payload.topic_id)
    if not topic:
        raise HTTPException(404, "题目不存在")
    keywords = f"\n建议覆盖的关键词:{', '.join(topic.keywords)}" if topic.keywords else ""
    user = f"题目:{topic.title}(CEFR {topic.level})\n要求:{topic.prompt}{keywords}"
    return SampleOut(essay=generate_text(ESSAY_SAMPLE_SYSTEM, user))
