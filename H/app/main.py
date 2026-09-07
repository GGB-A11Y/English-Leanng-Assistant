"""英语学习助手后端入口。

启动:在 H 目录下执行
    uvicorn app.main:app --host 127.0.0.1 --port 8000
接口契约见 Q/app/docs/API.md;前端 Vite dev server 将 /api/* 代理到本服务。
"""
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import SessionLocal, init_db
from .llm import LLMError
from .models import Quiz, ReadingArticle
from .routers import auth, chat, health, reading, translate, vocabulary, writing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="英语学习助手后端", version="0.1.0")
init_db()

logger = logging.getLogger(__name__)


def _cleanup_stale_rows():
    """启动时清理过期数据(自测与阅读文章无长期保留价值,避免 DB 无限增长)。"""
    db = SessionLocal()
    try:
        now = datetime.now()
        n_quiz = (
            db.query(Quiz)
            .filter(Quiz.created_at < now - timedelta(days=7))
            .delete(synchronize_session=False)
        )
        n_article = (
            db.query(ReadingArticle)
            .filter(ReadingArticle.created_at < now - timedelta(days=30))
            .delete(synchronize_session=False)
        )
        db.commit()
        if n_quiz or n_article:
            logger.info("[cleanup] 清理过期数据:自测 %d 条、阅读文章 %d 篇", n_quiz, n_article)
    finally:
        db.close()


_cleanup_stale_rows()
if not settings.llm_api_key:
    logger.warning(
        "未检测到环境变量 LLM_API_KEY / DEEPSEEK_API_KEY,AI 生成类接口(对话/词条/翻译/批改/文章)将不可用。"
        "设置方式见 README「密钥安全设置」。"
    )

# 开发环境经 Vite 代理无需 CORS;独立部署前端时通过 .env 的 CORS_ORIGINS 收紧来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """LLM 生成失败统一映射为 502 + {"detail": "..."}(契约第 1 / 6 节)。"""
    return JSONResponse(status_code=502, content={"detail": str(exc)})


for module in (health, auth, chat, vocabulary, translate, writing, reading):
    app.include_router(module.router, prefix="/api")
