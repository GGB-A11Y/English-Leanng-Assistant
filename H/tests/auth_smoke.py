"""认证与多用户隔离冒烟测试(无 pytest 依赖,直接运行)。

用法(在 H 目录,项目根含空格须加引号):
    "..\\..\\.venv\\Scripts\\python.exe" tests\\auth_smoke.py
    (或 `..\.venv\Scripts\python tests\auth_smoke.py`)

使用独立临时库 H/test_smoke.db,不影响开发库 english_learning.db。
"""
import os
import sys

H_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H_DIR)
os.environ["DATABASE_URL"] = "sqlite:///./test_smoke.db"  # 必须在 import app 之前注入

# 清理上次运行残留(上次进程结束前若未删干净,这里兜底)
_stale = os.path.join(H_DIR, "test_smoke.db")
if os.path.exists(_stale):
    os.remove(_stale)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

# 路由层的图形验证码校验置为恒真(真实实现由第 5 节单元往返覆盖);
# 必须 patch routers.auth 模块级名字(路由体以该名字调用),与 send_reset_email 同模式
import app.routers.auth as auth_router  # noqa: E402

auth_router.verify_captcha = lambda db, cid, code: True  # type: ignore

PASSED = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASSED
    if not cond:
        print(f"  [FAIL] {name} {detail}")
        sys.exit(1)
    PASSED += 1
    print(f"  [ok] {name}")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(email: str, password: str = "password123"):
    # 验证码校验已被 monkeypatch 为恒真,id/code 传占位即可
    return client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "captcha_id": "c_test",
        "captcha_code": "TEST",
    })


print("== 1. 注册 / 登录 / me / 登出 ==")
r = register("alice@example.com")
check("注册返回 token", r.status_code == 200 and r.json().get("token"), str(r.json()))
alice_token = r.json()["token"]
check("注册返回用户信息", r.json()["user"]["email"] == "alice@example.com")
check("重复注册 409", register("ALICE@example.com").status_code == 409, "邮箱应大小写不敏感")
check("弱密码 422", register("bob@example.com", "short").status_code == 422)
check("非法邮箱 422", register("not-an-email", "password123").status_code == 422)

r = client.get("/api/auth/me", headers=auth(alice_token))
check("me 返回当前用户", r.status_code == 200 and r.json()["email"] == "alice@example.com")
check("无 token 401", client.get("/api/auth/me").status_code == 401)
check("坏 token 401", client.get("/api/auth/me", headers=auth("bad")).status_code == 401)

r = client.post("/api/auth/logout", headers=auth(alice_token))
check("登出成功", r.status_code == 200)
check("登出后 token 失效", client.get("/api/auth/me", headers=auth(alice_token)).status_code == 401)

print("== 1.5 图形验证码(路由层,校验已 monkeypatch) ==")
r = client.get("/api/auth/captcha")
check("获取验证码 200", r.status_code == 200)
data = r.json()
check("返回 captcha_id 与 SVG data URI", bool(data.get("captcha_id"))
      and str(data.get("image", "")).startswith("data:image/svg+xml;base64,"))
check("响应头 no-store", r.headers.get("cache-control", "").lower() == "no-store")
r = client.post("/api/auth/register", json={"email": "carol-captcha@example.com", "password": "password123"})
check("缺少验证码字段 422", r.status_code == 422)  # Pydantic 必填,不消耗验证码
auth_router.verify_captcha = lambda db, cid, code: False  # type: ignore
r = register("carol-captcha@example.com")
check("验证码校验失败 400", r.status_code == 400 and "验证码" in r.json()["detail"])
auth_router.verify_captcha = lambda db, cid, code: True  # type: ignore
check("恢复恒真后注册可用", register("carol-captcha@example.com").status_code == 200)

print("== 2. 登录与锁定节流 ==")
for i in range(4):
    r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong-pass"})
    check(f"第 {i+1} 次错密码 401", r.status_code == 401)
r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong-pass"})
check("第 5 次错密码触发锁定 403", r.status_code == 403)
r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
check("锁定期间正确密码也 403", r.status_code == 403)
r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
check("不存在用户 401", r.status_code == 401)

print("== 3. 密码重置(monkeypatch 发信) ==")
sent: list = []
auth_router.send_reset_email = lambda to, token: sent.append((to, token))  # type: ignore

r = client.post("/api/auth/reset/request", json={"email": "alice@example.com"})
check("重置请求(锁定中仍可发)返回统一文案", r.status_code == 200 and "邮件" in r.json()["message"])
check("邮件已发出", len(sent) == 1 and sent[0][0] == "alice@example.com")
check("60s 内重复请求 429", client.post("/api/auth/reset/request", json={"email": "alice@example.com"}).status_code == 429)
check("未注册邮箱返回同一文案", client.post("/api/auth/reset/request", json={"email": "ghost@example.com"}).status_code == 200)

reset_token = sent[0][1]
r = client.post("/api/auth/reset/confirm", json={"token": reset_token, "new_password": "new-password-1"})
check("重置确认成功", r.status_code == 200)
r = client.post("/api/auth/reset/confirm", json={"token": reset_token, "new_password": "new-password-2"})
check("重置 token 一次性", r.status_code == 400)
r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "new-password-1"})
check("新密码登录成功(锁定随改密清除)", r.status_code == 200)
alice_token = r.json()["token"]

print("== 4. 多用户数据隔离 ==")
r = register("bob@example.com")
bob_token = r.json()["token"]

r = client.post("/api/vocabulary/words/import", json={"stage": "primary"}, headers=auth(alice_token))
check("A 导入词库", r.status_code == 200 and r.json()["imported"] > 0, str(r.json()))

r = client.get("/api/vocabulary/words", headers=auth(alice_token))
check("A 看到自己导入的单词", r.json()["total"] > 0)
r = client.get("/api/vocabulary/words", headers=auth(bob_token))
check("B 单词列表为空", r.json()["total"] == 0, f"total={r.json()['total']}")

r = client.get("/api/vocabulary/builtin", headers=auth(bob_token))
check("B 的内置词库导入计数为 0", all(s["imported"] == 0 for s in r.json()["stages"]))

r = client.post("/api/chat/sessions", headers=auth(alice_token))
aid = r.json()["id"]
check("A 建会话成功", r.status_code == 200)
check("B 看不到 A 的会话", client.get(f"/api/chat/sessions/{aid}", headers=auth(bob_token)).status_code == 404)
check("B 删 A 的会话 404", client.delete(f"/api/chat/sessions/{aid}", headers=auth(bob_token)).status_code == 404)
check("A 自己的会话可见", client.get(f"/api/chat/sessions/{aid}", headers=auth(alice_token)).status_code == 200)

r = client.post("/api/writing/topics", json={
    "title": "Alice's Topic", "stage": "junior", "prompt": "Write about it.", "keywords": []
}, headers=auth(alice_token))
check("A 自建作文题", r.status_code == 200)
atopic = r.json()["id"]

r = client.get("/api/writing/topics", headers=auth(bob_token))
titles = [t["title"] for t in r.json()["topics"]]
check("B 只见内置题,看不到 A 的题", "Alice's Topic" not in titles and len(titles) == 15, str(len(titles)))
check("B 修改内置题 403", client.patch("/api/writing/topics/t_1", json={"groups": ["x"]}, headers=auth(bob_token)).status_code == 403)
check("B 删除内置题 403", client.delete("/api/writing/topics/t_1", headers=auth(bob_token)).status_code == 403)
check("B 删 A 的自建题 404", client.delete(f"/api/writing/topics/{atopic}", headers=auth(bob_token)).status_code == 404)
check("A 删自己的题成功", client.delete(f"/api/writing/topics/{atopic}", headers=auth(alice_token)).status_code == 200)

r = client.post("/api/vocabulary/groups", json={"name": "同名分组"}, headers=auth(alice_token))
check("A 建分组", r.status_code == 200)
check("B 建同名分组不冲突", client.post("/api/vocabulary/groups", json={"name": "同名分组"}, headers=auth(bob_token)).status_code == 200)
check("A 同名分组再建 409", client.post("/api/vocabulary/groups", json={"name": "同名分组"}, headers=auth(alice_token)).status_code == 409)

r = client.get("/api/vocabulary/quiz?count=5", headers=auth(alice_token))
quiz_id = r.json()["quiz_id"]
check("A 开自测", r.status_code == 200)
check("B 提交 A 的 quiz 404", client.post(f"/api/vocabulary/quiz/{quiz_id}/submit", json={"answers": []}, headers=auth(bob_token)).status_code == 404)
r = client.post(f"/api/vocabulary/quiz/{quiz_id}/submit", json={"answers": []}, headers=auth(alice_token))
check("A 提交自己的 quiz 成功", r.status_code == 200)

print("== 5. captcha.py 单元往返(真实实现) ==")
# 从 captcha 模块导入真函数:与路由层被 patch 的副本(auth_router.verify_captcha)互不干扰
import base64  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

from app.auth import hash_token  # noqa: E402
from app.captcha import CHARS, create_captcha, generate, verify_captcha  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Captcha, gen_id  # noqa: E402

db = SessionLocal()
answer, svg = generate()
check("generate 4 位合法字符", len(answer) == 4 and all(c in CHARS for c in answer))
check("SVG 含 svg 标记", "<svg" in svg and "</svg>" in svg)
cap_id, data_uri = create_captcha(db)
check("create_captcha 返回 data URI", data_uri.startswith("data:image/svg+xml;base64,"))
check("data URI 可解出 SVG", "<svg" in base64.b64decode(data_uri.split(",", 1)[1]).decode("utf-8"))

aid = gen_id("c")
db.add(Captcha(id=aid, answer_hash=hash_token("AB2Z"), created_at=datetime.now()))
db.commit()
check("正确答案通过", verify_captcha(db, aid, "AB2Z") is True)
check("一次性:再用即失效", verify_captcha(db, aid, "ab2z") is False)
bid = gen_id("c")
db.add(Captcha(id=bid, answer_hash=hash_token("C7KM"), created_at=datetime.now()))
db.commit()
check("小写输入通过(大小写不敏感)", verify_captcha(db, bid, "c7km") is True)
check("错误答案 False 且行已删除", verify_captcha(db, bid, "9999") is False)
cid2 = gen_id("c")
db.add(Captcha(id=cid2, answer_hash=hash_token("D4NP"),
               created_at=datetime.now() - timedelta(minutes=settings.captcha_expire_minutes + 1)))
db.commit()
check("过期验证码 False", verify_captcha(db, cid2, "D4NP") is False)
check("不存在的 id False", verify_captcha(db, "c_none", "D4NP") is False)
db.close()

print(f"\n全部通过:{PASSED} 项断言")
# 清理临时库:先 dispose 引擎释放文件句柄(Windows 上不释放则删不掉)
from app.database import engine  # noqa: E402

engine.dispose()
try:
    os.remove(os.path.join(H_DIR, "test_smoke.db"))
except OSError:
    pass
