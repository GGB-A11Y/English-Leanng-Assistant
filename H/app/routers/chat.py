"""AI 对话:会话 CRUD + SSE 流式消息(契约 docs/API.md 2 / 3.2)。

SSE 帧格式:data: {"type":"delta"|"done"|"error"} 每帧以 \\n\\n 结束,
心跳用注释行 ": ping"(每 20s);客户端断开时中止 LLM 生成。
"""
import asyncio
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..llm import build_llm
from ..models import ChatMessage, ChatSession, User
from ..prompts import CHAT_SYSTEM
from ..schemas import ChatMessageIn, MessageOut, SessionDetailOut, SessionListItem, SessionOut, iso

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 20

_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def _safe_title(content: str, limit: int = 30) -> str:
    """截取会话标题:先剔除孤立代理项(JS 传入畸形 JSON 时可能产生),
    避免 SQLite 以 UTF-8 写入时因孤立代理抛 UnicodeEncodeError。"""
    return _SURROGATE_RE.sub("", content[:limit])


def session_to_list_item(s: ChatSession) -> SessionListItem:
    return SessionListItem(
        id=s.id, title=s.title, created_at=iso(s.created_at), message_count=len(s.messages)
    )


def session_to_detail(s: ChatSession) -> SessionDetailOut:
    messages = [
        MessageOut(id=m.id, role=m.role, content=m.content, created_at=iso(m.created_at))
        for m in s.messages
    ]
    return SessionDetailOut(
        id=s.id, title=s.title, created_at=iso(s.created_at), messages=messages
    )


def _get_owned_session_or_404(session_id: str, user: User, db: Session) -> ChatSession:
    """会话归属校验:不存在或不属于当前用户一律 404(不泄露存在性)。"""
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    return session


@router.post("/chat/sessions", response_model=SessionOut)
def create_session(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = ChatSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut(id=session.id, title=session.title, created_at=iso(session.created_at))


@router.get("/chat/sessions", response_model=list[SessionListItem])
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [session_to_list_item(s) for s in sessions]


@router.get("/chat/sessions/{session_id}", response_model=SessionDetailOut)
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return session_to_detail(_get_owned_session_or_404(session_id, user, db))


@router.delete("/chat/sessions/{session_id}")
def delete_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = _get_owned_session_or_404(session_id, user, db)
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.post("/chat/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    payload: ChatMessageIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_owned_session_or_404(session_id, user, db)
    content = payload.content.strip()
    if not content:
        raise HTTPException(422, "消息内容不能为空")
    if len(content) > 4000:
        raise HTTPException(422, "消息过长(最多 4000 字符)")

    # 落库用户消息;首条消息生成会话标题
    # 以「是否首条」判断,而非比对默认标题,避免首条消息内容恰为"新对话"的边缘情况
    is_first = (
        db.query(ChatMessage).filter(ChatMessage.session_id == session.id).first() is None
    )
    db.add(ChatMessage(session_id=session.id, role="user", content=content))
    if is_first:
        session.title = _safe_title(content)
    db.commit()

    # 对话历史(最近 N 轮,含刚保存的用户消息)作为 LLM 上下文
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(settings.chat_history_turns * 2)
        .all()
    )
    history = list(reversed(history))
    # 偶数截断或错误路径的部分保存可能让窗口以 assistant 开头,裁掉保证以 user 开头
    while history and history[0].role != "user":
        history.pop(0)
    lc_history = [SystemMessage(content=CHAT_SYSTEM)] + [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in history
    ]

    async def event_stream():
        full = ""
        saved = False  # assistant 消息是否已落库(done/error 路径置 True)
        usage: dict = {}
        queue: asyncio.Queue = asyncio.Queue()

        async def produce():
            """独立任务跑 LLM 流式生成;客户端断开时由外层 cancel 中止。"""
            try:
                async for chunk in build_llm().astream(lc_history):
                    # usage 只在最后一个 chunk 出现(stream_usage=True),须在 text 判空前读取
                    um = getattr(chunk, "usage_metadata", None)
                    if um is not None:
                        usage["prompt_tokens"] = getattr(um, "input_tokens", None)
                        usage["completion_tokens"] = getattr(um, "output_tokens", None)
                    text = chunk.content if isinstance(chunk.content, str) else ""
                    if not text:
                        continue
                    await queue.put(("delta", text))
                await queue.put(("done", None))
            except Exception as exc:  # noqa: BLE001 生成异常统一走 error 帧
                logger.warning("对话生成异常: %s", exc)
                await queue.put(("error", "生成失败,请重试"))

        task = asyncio.create_task(produce())
        try:
            while True:
                try:
                    kind, payload_item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"  # 心跳注释行,防止代理超时(契约第 2 节)
                    continue

                if kind == "delta":
                    full += payload_item
                    yield f"data: {json.dumps({'type': 'delta', 'content': payload_item}, ensure_ascii=False)}\n\n"
                elif kind == "done":
                    if not full:
                        yield 'data: {"type": "error", "message": "生成失败,请重试"}\n\n'
                        return
                    msg = ChatMessage(session_id=session.id, role="assistant", content=full)
                    db.add(msg)
                    db.commit()
                    saved = True
                    yield f"data: {json.dumps({'type': 'done', 'message_id': msg.id, 'usage': usage}, ensure_ascii=False)}\n\n"
                    return
                else:  # error
                    if full:  # 生成到一半失败:保留部分内容
                        db.add(ChatMessage(session_id=session.id, role="assistant", content=full))
                        db.commit()
                        saved = True
                    yield f"data: {json.dumps({'type': 'error', 'message': payload_item}, ensure_ascii=False)}\n\n"
                    return
        finally:
            # 客户端断开(点击「停止生成」)→ 中止 LLM 生成(契约第 2 节)
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            # 停止生成时保留已生成的部分内容,与 error 帧路径行为一致
            # (否则刷新页面后部分回复消失,历史不完整)
            if full and not saved:
                try:
                    db.add(ChatMessage(session_id=session.id, role="assistant", content=full))
                    db.commit()
                except Exception:  # noqa: BLE001 客户端已断开,落库失败不阻塞
                    db.rollback()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
