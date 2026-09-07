"""发信通道自测:给任意邮箱发一封测试邮件,验证 RESEND_API_KEY 与 RESEND_FROM 配置。

用法(在 H 目录;设置过环境变量后请先重开终端,否则读不到新密钥):
    ..\\.venv\\Scripts\\python tests\\send_test_email.py 收件邮箱

例如:
    ..\\.venv\\Scripts\\python tests\\send_test_email.py 123456@qq.com
"""
import os
import sys

H_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H_DIR)
os.chdir(H_DIR)  # 让 pydantic-settings 找到 H/.env

import resend  # noqa: E402

from app.config import settings  # noqa: E402

to = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
if not to or "@" not in to:
    print("用法: python tests/send_test_email.py 收件邮箱")
    sys.exit(1)

if not settings.resend_api_key:
    print("[失败] 未读到 RESEND_API_KEY:设置环境变量后请重开终端再运行")
    sys.exit(1)

print(f"密钥: {settings.resend_api_key[:4]}*** (长度 {len(settings.resend_api_key)})")
print(f"发信地址: {settings.resend_from}")
print(f"收件人: {to}")

resend.api_key = settings.resend_api_key
try:
    r = resend.Emails.send({
        "from": settings.resend_from,
        "to": to,
        "subject": "英语学习助手 — 发信通道测试",
        "html": "<p>这是一封测试邮件:你的 Resend 密钥与域名配置已生效 ✅</p>",
        "text": "这是一封测试邮件:你的 Resend 密钥与域名配置已生效",
    })
    print(f"[成功] 已发送,Resend 邮件 id: {r.get('id')}")
    print("请检查收件箱(可能在垃圾箱);没收到可去 resend.com → Emails 查看投递状态")
except Exception as exc:  # noqa: BLE001
    print(f"[失败] {exc}")
    print("常见原因:1) RESEND_FROM 域名未验证 2) 密钥是测试模式且收件人不是 Resend 账号邮箱 "
          "3) 密钥无效(需换成 Production 密钥)")
    sys.exit(1)
