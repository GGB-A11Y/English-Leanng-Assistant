"""认证:注册 / 登录 / 登出 / 当前用户 / 密码重置(邮件一次性链接,契约 3.7)。

安全设计:
- 邮箱统一小写;密码 8~128 字符(bcrypt 72 字节限制由 auth.py 的 sha256 预哈希消化)
- 登录节流:连续失败 >= 阈值锁定账号若干分钟;用户不存在时跑一次假 bcrypt 防时序枚举
- 重置接口:存在与否返回同一文案防枚举;每邮箱 60s 限频;改密后吊销全部会话
"""
import logging
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..auth import (
    create_reset_token, create_session, get_current_user, hash_password,
    hash_token, verify_password,
)
from ..config import settings
from ..database import get_db
from ..email import send_reset_email
from ..models import AuthSession, PasswordResetToken, User
from ..schemas import (
    LoginIn, RegisterIn, ResetConfirmIn, ResetRequestIn, TokenOut, UserOut, iso,
)

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128

# 防时序枚举:用户不存在时也执行一次等价的 bcrypt 校验
_FAKE_HASH = hash_password("fake-password-for-timing-equalization")


def _validate_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(422, "邮箱格式不正确")
    return email


def _validate_password(password: str) -> None:
    if not MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN:
        raise HTTPException(422, f"密码长度需在 {MIN_PASSWORD_LEN}~{MAX_PASSWORD_LEN} 个字符之间")


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, created_at=iso(u.created_at) or "")


@router.post("/auth/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = _validate_email(payload.email)
    _validate_password(payload.password)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "该邮箱已注册,请直接登录")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session(db, user)
    return TokenOut(token=token, user=_user_out(user))


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = _validate_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        verify_password(payload.password, _FAKE_HASH)  # 防时序枚举
        raise HTTPException(401, "邮箱或密码错误")
    if user.locked_until and user.locked_until > datetime.now():
        raise HTTPException(403, "尝试次数过多,账号已临时锁定,请稍后再试")
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.login_lock_threshold:
            user.locked_until = datetime.now() + timedelta(minutes=settings.login_lock_minutes)
            user.failed_login_attempts = 0
            db.commit()
            raise HTTPException(403, f"尝试次数过多,账号已锁定 {settings.login_lock_minutes} 分钟")
        db.commit()
        raise HTTPException(401, "邮箱或密码错误")
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now()
    db.commit()
    token = create_session(db, user)
    return TokenOut(token=token, user=_user_out(user))


@router.post("/auth/logout")
def logout(
    user: User = Depends(get_current_user),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    token = (authorization or "").removeprefix("Bearer ").strip()
    session = db.get(AuthSession, hash_token(token))
    if session:
        db.delete(session)
        db.commit()
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.post("/auth/reset/request")
def reset_request(payload: ResetRequestIn, db: Session = Depends(get_db)):
    email = _validate_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if user:
        # 限频:查该用户最新的重置 token(60s 内只能发一封)
        latest = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == user.id)
            .order_by(PasswordResetToken.created_at.desc())
            .first()
        )
        if latest and (datetime.now() - latest.created_at).total_seconds() < settings.reset_email_interval_seconds:
            raise HTTPException(429, "发送过于频繁,请稍后再试")
        token = create_reset_token(db, user)
        try:
            send_reset_email(user.email, token)
        except Exception as exc:  # noqa: BLE001 发信失败:回滚该 token,明确报 503
            logger.warning("发送重置邮件失败: %s", exc)
            db.query(PasswordResetToken).filter(
                PasswordResetToken.token_hash == hash_token(token)
            ).delete()
            db.commit()
            raise HTTPException(503, "邮件发送失败,请稍后重试或确认邮件服务已配置")
    # 无论邮箱是否存在都返回同一文案(防枚举)
    return {"message": "如果该邮箱已注册,重置邮件将发送至您的邮箱,请查收"}


@router.post("/auth/reset/confirm")
def reset_confirm(payload: ResetConfirmIn, db: Session = Depends(get_db)):
    _validate_password(payload.new_password)
    row = db.get(PasswordResetToken, hash_token(payload.token))
    if not row or row.expires_at <= datetime.now():
        raise HTTPException(400, "重置链接无效或已过期,请重新申请")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(400, "重置链接无效或已过期,请重新申请")
    user.password_hash = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.delete(row)
    # 改密后吊销该用户全部会话,强制重新登录
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()
    return {"ok": True}
