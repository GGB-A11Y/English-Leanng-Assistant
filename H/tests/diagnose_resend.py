"""Resend 配置诊断:检查当前 RESEND_API_KEY 对应账号的域名与邮件记录(只读,不发信)。

用法(在 H 目录):
    ..\\.venv\\Scripts\\python tests\\diagnose_resend.py
"""
import os
import sys

H_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H_DIR)

import httpx  # noqa: E402

key = os.environ.get("RESEND_API_KEY", "")
if not key:
    # 当前进程读不到环境变量(旧终端):回退读 Windows 用户环境注册表
    import winreg  # noqa: E402

    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        with winreg.OpenKey(reg, r"Environment") as k:
            key, _ = winreg.QueryValueEx(k, "RESEND_API_KEY")
    except OSError:
        pass

if not key:
    print("[失败] 未找到 RESEND_API_KEY(环境变量与注册表都没有)")
    sys.exit(1)

print(f"当前密钥: {key[:4]}*** (长度 {len(key)})")
headers = {"Authorization": f"Bearer {key}"}
base = "https://api.resend.com"

with httpx.Client(timeout=20) as client:
    r = client.get(f"{base}/domains", headers=headers)
    print(f"\n== 域名列表(HTTP {r.status_code}) ==")
    if r.status_code == 200:
        domains = r.json().get("data") or []
        if not domains:
            print("  (空:该密钥账号下没有任何域名)")
        for d in domains:
            print(f"  - {d.get('name')}  status={d.get('status')}")
    else:
        print("  ", r.json())

    r = client.get(f"{base}/emails", params={"limit": 5}, headers=headers)
    print(f"\n== 最近 5 封邮件记录(HTTP {r.status_code}) ==")
    if r.status_code == 200:
        emails = r.json().get("data") or []
        if not emails:
            print("  (空:该密钥账号下没有任何邮件记录)")
        for e in emails:
            print(f"  - id={str(e.get('id'))[:8]}... from={e.get('from')} "
                  f"to={e.get('to')} last_event={e.get('last_event')}")
    else:
        print("  ", r.json())
