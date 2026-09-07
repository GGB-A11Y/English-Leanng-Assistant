"""ORM 模型(SQLite)。

id 采用带前缀的随机串,与契约示例(s_1 / w_1 / q_1)风格一致;
列表型字段以 JSON 列存储。
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> datetime:
    return datetime.now()


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("s"))
    title: Mapped[str] = mapped_column(String, default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("m"))
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    session: Mapped[ChatSession] = relationship(back_populates="messages")


class Word(Base):
    __tablename__ = "words"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("w"))
    word: Mapped[str] = mapped_column(String, unique=True, index=True)
    phonetic: Mapped[str] = mapped_column(String, default="")
    pos: Mapped[str] = mapped_column(String, default="")
    definition_cn: Mapped[str] = mapped_column(String, default="")
    definition_en: Mapped[str] = mapped_column(String, default="")
    examples: Mapped[list] = mapped_column(JSON, default=list)
    roots_affixes: Mapped[list] = mapped_column(JSON, default=list)
    synonyms: Mapped[list] = mapped_column(JSON, default=list)
    antonyms: Mapped[list] = mapped_column(JSON, default=list)
    collocations: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    groups: Mapped[list] = mapped_column(JSON, default=list)  # 用户自定义分组名列表
    note: Mapped[str] = mapped_column(String, default="")

    # SM-2 复习状态
    familiarity: Mapped[int] = mapped_column(Integer, default=0)     # 最近一次评分 0~5
    repetition: Mapped[int] = mapped_column(Integer, default=0)      # 连续成功次数
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)   # EF,下限 1.3
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class WordGroup(Base):
    """用户自定义分组(单词与分组的归属存在 Word.groups 上)。"""

    __tablename__ = "word_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("g"))
    name: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("q"))
    questions: Mapped[list] = mapped_column(JSON, default=list)  # [{word, phonetic, options}]
    answers: Mapped[list] = mapped_column(JSON, default=list)    # [{word, answer}]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ReadingArticle(Base):
    __tablename__ = "reading_articles"

    article_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("a"))
    title: Mapped[str] = mapped_column(String, default="")
    level: Mapped[str] = mapped_column(String, default="")   # CEFR 等级(内部生成用)
    stage: Mapped[str] = mapped_column(String, default="")   # 学段:primary/junior/senior
    content: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    # 每题为 {id, type, question, options, correct_answer, explanation}
    # 正确答案与解析仅存服务端,判分零 LLM 成本(契约 3.6 设计约定)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    vocabulary_notes: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class WritingTopic(Base):
    __tablename__ = "writing_topics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    level: Mapped[str] = mapped_column(String)
    stage: Mapped[str] = mapped_column(String, default="")  # 学段:primary/junior/senior
    prompt: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    groups: Mapped[list] = mapped_column(JSON, default=list)  # 用户自定义分组名列表


class TopicGroup(Base):
    """作文题目的用户自定义分组(归属存在 WritingTopic.groups 上)。"""

    __tablename__ = "topic_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("tg"))
    name: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
