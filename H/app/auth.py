"""认证工具:密码哈希、会话 token、重置 token 与「当前用户」依赖。

设计:
- 密码:bcrypt(bcrypt 5.0 限制 72 字节输入,按官方推荐先 sha256 预哈希再 bcrypt,
  注册/登录/改密同口径,对外校验 8~128 字符)
- 会话 token:secrets.token_urlsafe(32),库存 SHA-256 哈希(库文件泄露也拿不到明文)
- get_current_user:FastAPI 依赖,Bearer → auth_sessions 查哈希 → users,失败一律 401
"""
import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import AuthSession, PasswordResetToken, User


def _prehash(password: str) -> bytes:
    """sha256 预哈希:hexdigest 为 64 位 ASCII,落在 bcrypt 的 72 字节限制内。"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("ascii"))
    except ValueError:  # 非法的哈希串
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> str:
    """创建登录会话,返回明文 token(仅此一次可见,库中只存哈希)。"""
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(
        token_hash=hash_token(token),
        user_id=user.id,
        expires_at=datetime.now() + timedelta(days=settings.session_expire_days),
    ))
    db.commit()
    return token


def create_reset_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        token_hash=hash_token(token),
        user_id=user.id,
        expires_at=datetime.now() + timedelta(minutes=settings.reset_token_expire_minutes),
    ))
    db.commit()
    return token


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """当前登录用户依赖:所有受保护路由挂 Depends(get_current_user)。

    SSE 路由同样适用(鉴权在流开始前完成)。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    token = authorization[len("Bearer "):].strip()
    session = db.get(AuthSession, hash_token(token))
    if not session or session.expires_at <= datetime.now():
        raise HTTPException(401, "登录已过期,请重新登录")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "用户不存在")
    return user
