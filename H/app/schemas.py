"""Pydantic 契约模型(与前端 Q/app/docs/API.md 一一对应)。

- *_Llm:LLM 结构化输出的 schema(生成类接口)
- *_Out / *_In:对外响应与请求体
"""
from typing import Literal

from pydantic import BaseModel, Field

CEFR = Literal["A1", "A2", "B1", "B2", "C1"]


# ==================== LLM 结构化输出 ====================

class ExampleLlm(BaseModel):
    sentence: str
    translation: str = ""


class RootAffixLlm(BaseModel):
    part: str
    meaning: str
    words: list[str] = Field(default_factory=list)


class WordEntryLlm(BaseModel):
    phonetic: str = ""
    pos: str = ""
    definition_cn: str = ""
    definition_en: str = ""
    examples: list[ExampleLlm] = Field(default_factory=list)
    roots_affixes: list[RootAffixLlm] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    collocations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class PhraseLlm(BaseModel):
    phrase: str
    meaning: str
    note: str = ""


class GrammarPointLlm(BaseModel):
    point: str
    explanation: str


class KeyWordLlm(BaseModel):
    word: str
    phonetic: str = ""
    meaning: str


class ExplanationLlm(BaseModel):
    phrases: list[PhraseLlm] = Field(default_factory=list)
    grammar_points: list[GrammarPointLlm] = Field(default_factory=list)
    key_words: list[KeyWordLlm] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)


class TranslationLlm(BaseModel):
    translation: str
    explanation: ExplanationLlm = Field(default_factory=ExplanationLlm)


class CorrectionLlm(BaseModel):
    original: str
    corrected: str
    explanation: str = ""
    type: Literal["grammar", "word_choice", "spelling"] = "grammar"


class VocabSuggestionLlm(BaseModel):
    original: str
    suggestion: str
    reason: str = ""


class EssayFeedbackLlm(BaseModel):
    overall_comment: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    corrections: list[CorrectionLlm] = Field(default_factory=list)
    vocabulary_suggestions: list[VocabSuggestionLlm] = Field(default_factory=list)
    improved_version: str = ""


class EssayGradeLlm(BaseModel):
    score: int = Field(ge=0, le=100)
    level: CEFR = "B1"
    feedback: EssayFeedbackLlm = Field(default_factory=EssayFeedbackLlm)


class QuestionLlm(BaseModel):
    type: Literal["single_choice", "true_false"]
    question: str
    options: list[str] = Field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""


class VocabNoteLlm(BaseModel):
    word: str
    meaning: str


class ArticleLlm(BaseModel):
    title: str
    level: CEFR = "B1"
    content: str
    questions: list[QuestionLlm] = Field(default_factory=list)
    vocabulary_notes: list[VocabNoteLlm] = Field(default_factory=list)


# ==================== 请求体 ====================

class WordCreateIn(BaseModel):
    word: str


class StageImportIn(BaseModel):
    stage: str


class WordPatchIn(BaseModel):
    tags: list[str] | None = None
    groups: list[str] | None = None
    note: str | None = None


class GroupCreateIn(BaseModel):
    name: str


class ReviewSubmitIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class QuizSubmitIn(BaseModel):
    answers: list[dict] = Field(default_factory=list)  # [{word, answer_index}]


class ChatMessageIn(BaseModel):
    content: str


class TranslateIn(BaseModel):
    text: str
    source_lang: Literal["zh", "en"]
    target_lang: Literal["zh", "en"]


class EssayGradeIn(BaseModel):
    topic_id: str | None = None
    title: str = ""
    content: str
    requirement: str = ""
    stage: Literal["primary", "junior", "senior"] | None = None  # 学生学段(评分参照)


class EssaySampleIn(BaseModel):
    topic_id: str


# ==================== 自定义作文题目 ====================

class TopicItemLlm(BaseModel):
    """AI 批量解析题目素材的输出结构。"""
    title: str
    level: CEFR = "B1"
    prompt: str
    keywords: list[str] = Field(default_factory=list)


class TopicListLlm(BaseModel):
    topics: list[TopicItemLlm] = Field(default_factory=list)


class TopicCreateIn(BaseModel):
    title: str
    stage: Literal["primary", "junior", "senior"]
    prompt: str
    keywords: list[str] = Field(default_factory=list)


class TopicImportItemIn(BaseModel):
    title: str
    level: CEFR = "B1"
    prompt: str
    keywords: list[str] = Field(default_factory=list)


class TopicImportIn(BaseModel):
    topics: list[TopicImportItemIn]


class TopicParseIn(BaseModel):
    text: str


class ArticleGenerateIn(BaseModel):
    """阅读理解生成请求:学段(stage)与 CEFR 等级(level)二选一,stage 优先。"""
    stage: Literal["primary", "junior", "senior"] | None = None
    level: CEFR | None = None
    topic: str = ""


class ArticleSubmitIn(BaseModel):
    answers: list[dict] = Field(default_factory=list)  # [{question_id, answer}]


# ==================== 认证(契约 3.7) ====================

class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class ResetRequestIn(BaseModel):
    email: str


class ResetConfirmIn(BaseModel):
    token: str
    new_password: str


class UserOut(BaseModel):
    id: str
    email: str
    created_at: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ==================== 对外响应(契约) ====================

class WordOut(BaseModel):
    id: str
    word: str
    phonetic: str = ""
    pos: str = ""
    definition_cn: str = ""
    definition_en: str = ""
    examples: list[ExampleLlm] = Field(default_factory=list)
    roots_affixes: list[RootAffixLlm] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    collocations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    note: str = ""
    familiarity: int = 0
    repetition: int = 0
    next_review_at: str | None = None
    created_at: str


class WordPage(BaseModel):
    items: list[WordOut]
    total: int
    page: int
    page_size: int


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str


class SessionListItem(SessionOut):
    message_count: int = 0


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class SessionDetailOut(SessionOut):
    messages: list[MessageOut] = Field(default_factory=list)


class ReviewItemOut(BaseModel):
    id: str
    word: str
    phonetic: str = ""
    definition_cn: str = ""
    familiarity: int = 0
    repetition: int = 0


class ReviewQueueOut(BaseModel):
    items: list[ReviewItemOut]
    due_count: int
    total_count: int


class ReviewResultOut(BaseModel):
    id: str
    familiarity: int
    repetition: int
    ease_factor: float
    interval_days: int
    next_review_at: str
    is_mastered: bool


class QuizQuestionOut(BaseModel):
    word: str
    phonetic: str = ""
    options: list[str]


class QuizStartOut(BaseModel):
    quiz_id: str
    questions: list[QuizQuestionOut]


class QuizResultItemOut(BaseModel):
    word: str
    correct: bool
    your_answer: str | None = None
    correct_answer: str


class QuizSubmitOut(BaseModel):
    score: int
    total: int
    results: list[QuizResultItemOut]


class TopicOut(BaseModel):
    id: str
    title: str
    level: str
    stage: str = ""
    prompt: str
    keywords: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)


class TopicPatchIn(BaseModel):
    groups: list[str] | None = None


class TopicsOut(BaseModel):
    topics: list[TopicOut]


class SampleOut(BaseModel):
    essay: str


class ArticleOut(BaseModel):
    article_id: str
    title: str
    level: str
    stage: str = ""
    content: str
    word_count: int
    questions: list[dict]  # 不含 correct_answer/explanation(仅服务端存储)
    vocabulary_notes: list[dict]


class ArticleResultItemOut(BaseModel):
    question_id: str
    correct: bool
    your_answer: str | None = None
    correct_answer: str
    explanation: str = ""


class ArticleSubmitOut(BaseModel):
    score: int
    total: int
    results: list[ArticleResultItemOut]


# ==================== 序列化辅助 ====================

def iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.astimezone().isoformat(timespec="seconds")


def word_to_out(w) -> WordOut:
    """ORM Word → 契约响应(契约见 API.md 3.3)。"""
    return WordOut(
        id=w.id,
        word=w.word,
        phonetic=w.phonetic or "",
        pos=w.pos or "",
        definition_cn=w.definition_cn or "",
        definition_en=w.definition_en or "",
        examples=w.examples or [],
        roots_affixes=w.roots_affixes or [],
        synonyms=w.synonyms or [],
        antonyms=w.antonyms or [],
        collocations=w.collocations or [],
        tags=w.tags or [],
        groups=w.groups or [],
        note=w.note or "",
        familiarity=w.familiarity or 0,
        repetition=w.repetition or 0,
        next_review_at=iso(w.next_review_at),
        created_at=iso(w.created_at) or "",
    )
