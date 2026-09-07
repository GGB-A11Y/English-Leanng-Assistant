"""邮件发送(Resend)。

- 密钥走环境变量 RESEND_API_KEY(与 LLM 密钥同一约定,不落 .env 文件)
- 测试模式:from 用 onboarding@resend.dev,只能发给 Resend 账号本人邮箱
- 生产:需在 Resend 验证域名(腾讯云 DNS 配置见 docs/resend-tencent-dns.md),
  并把 RESEND_FROM 改为自有地址
"""
import logging

import resend

from .config import settings

logger = logging.getLogger(__name__)

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


def send_reset_email(to: str, token: str) -> None:
    """发送密码重置邮件。RESEND_API_KEY 未配置时抛 RuntimeError(路由转 503)。"""
    if not settings.resend_api_key:
        raise RuntimeError("邮件服务未配置(缺少环境变量 RESEND_API_KEY)")
    link = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    minutes = settings.reset_token_expire_minutes
    resend.Emails.send({
        "from": settings.resend_from,
        "to": to,
        "subject": "英语学习助手 — 重置密码",
        "html": (
            "<p>您好,我们收到了您的密码重置请求。</p>"
            f"<p>请在 {minutes} 分钟内点击以下链接设置新密码:</p>"
            f'<p><a href="{link}">{link}</a></p>'
            "<p>如果这不是您本人的操作,请忽略本邮件。</p>"
        ),
        "text": (
            f"您好,我们收到了您的密码重置请求。\n"
            f"请在 {minutes} 分钟内打开以下链接设置新密码:\n{link}\n"
            "如果这不是您本人的操作,请忽略本邮件。"
        ),
    })
    logger.info("已发送密码重置邮件至 %s", to)
