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
    return client.post("/api/auth/register", json={"email": email, "password": password})


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
import app.routers.auth as auth_router  # noqa: E402

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

print(f"\n全部通过:{PASSED} 项断言")
# 清理临时库:先 dispose 引擎释放文件句柄(Windows 上不释放则删不掉)
from app.database import engine  # noqa: E402

engine.dispose()
try:
    os.remove(os.path.join(H_DIR, "test_smoke.db"))
except OSError:
    pass
