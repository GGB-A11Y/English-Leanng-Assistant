# 英语学习助手 — 后端(LangChain / FastAPI)

与前端 `Q/app` 配套的后端服务,接口契约见 **`Q/app/docs/API.md`**(以该文档为准,本 README 仅作运行说明)。

## 快速开始

虚拟环境在**项目根目录** `.venv`(PyCharm 自动创建并管理,依赖已全部装好)。
新机器上重建环境:

```bash
cd "English Leanng Assistant"      # 项目根目录
python -m venv .venv
.venv\Scripts\activate             # Windows;Linux/Mac 用 source .venv/bin/activate
pip install -r H\requirements.txt

copy H\.env.example H\.env         # 非敏感配置;密钥不走文件,见下方「密钥安全设置」
cd H
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端 `Q/app` 下 `npm run dev` 即可联调(Vite 已将 `/api/*` 代理到 8000 端口)。

### 密钥安全设置

LLM 密钥不写入 `.env` 文件(避免随项目复制/打包泄露),通过**系统环境变量**注入,
变量名 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY` 皆可(两者任设其一)。
配置优先级:环境变量 > .env 文件 > 代码默认值。任选一种方式:

1. **Windows 用户环境变量**(永久,设置后需重开终端/PyCharm):

   ```bat
   setx DEEPSEEK_API_KEY "sk-你的DeepSeek密钥"
   ```

2. **PyCharm 运行配置**:运行 → 编辑配置 → 环境变量,添加
   `DEEPSEEK_API_KEY=sk-你的DeepSeek密钥`(仅该运行配置生效,改动即时)。

密钥从 [platform.deepseek.com](https://platform.deepseek.com) 申请。
未设置密钥时服务仍可启动:健康检查、作文题库等非 LLM 接口可用,生成类接口返回 502。

**Resend 邮件密钥**(密码重置邮件用,可选):同样走系统环境变量 `RESEND_API_KEY`
(平台 [resend.com](https://resend.com))。未配置时注册/登录不受影响,仅重置密码接口返回 503;
域名验证与腾讯云 DNS 配置见 [`docs/resend-tencent-dns.md`](../docs/resend-tencent-dns.md)。

### 认证(邮箱 + 密码)

所有业务接口需 `Authorization: Bearer <token>`(登录/注册后获取,契约 3.7);
`/api/health` 与 `/api/auth/*` 为公开接口。数据按用户隔离:
内置作文题库全员共享,其余(单词本/对话/自测/阅读/自定义题目)每用户独立。

- 密码 bcrypt 哈希(sha256 预哈希,兼容 bcrypt 5.0 的 72 字节限制)
- 会话 token 与重置 token 只存 SHA-256 哈希;登录失败 5 次锁定 5 分钟;重置邮件每邮箱 60s 限 1 封
- **升级注意**:启动时自动执行多用户迁移(加 user_id 列/重建分组表/老数据打孤儿标记),
  升级前请备份 `english_learning.db`;老数据不会归属任何账号,如需把老单词本并入某个新账号,可手动执行:
  `UPDATE words SET user_id='<该用户的 id>' WHERE user_id IS NULL`(其他表同理)。

## 切换 LLM 提供商

后端走 OpenAI 兼容协议(经 `langchain-openai`),改 `.env` 即可:

| 提供商 | LLM_BASE_URL | LLM_MODEL |
|---|---|---|
| DeepSeek(默认) | https://api.deepseek.com | deepseek-chat |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus |
| 智谱 GLM | https://open.bigmodel.cn/api/paas/v4 | glm-4-plus |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |

## 目录结构

```
H/
├── app/
│   ├── main.py            # FastAPI 装配:CORS、LLMError→502、路由注册
│   ├── config.py          # 配置(.env 优先)
│   ├── database.py        # SQLite 引擎 / Session / init_db(含多用户迁移)
│   ├── models.py          # ORM:用户/会话/消息/单词/自测/阅读文章/作文题库
│   ├── schemas.py         # Pydantic 契约模型(与 API.md 一一对应)
│   ├── auth.py            # 密码哈希 / 会话与重置 token / get_current_user
│   ├── email.py           # Resend 邮件发送(密码重置)
│   ├── sm2.py             # SM-2 间隔重复算法
│   ├── llm.py             # LangChain 访问层(结构化输出 + 重试)
│   ├── prompts.py         # 各模块提示词
│   ├── seed_topics.py     # 作文题库种子(内置,无需 LLM)
│   └── routers/           # health / auth / chat / vocabulary / translate / writing / reading
├── tests/auth_smoke.py    # 认证与多用户隔离冒烟测试(独立临时库)
└── english_learning.db    # 运行后自动生成
```

## 关键实现说明

- **SSE 对话**(契约第 2 节):`data: {"type":"delta"|"done"|"error"}` 帧,`\n\n` 分隔,
  每 20s 心跳 `: ping`;客户端断开时取消 LLM 任务中止生成;部分内容也落库。
- **结构化输出**:`bind_tools` 强制函数调用 + DeepSeek 嵌套 JSON 字符串修复 + 时间预算内重试,
  仍失败返回 `502 {"detail": "生成失败,请重试"}`;阅读题目生成后做语义校验(选项数/答案在选项中),不合规重试。
- **SM-2**:EF 初始 2.5、下限 1.3;quality<3 重置 repetition;间隔 1 天 → 6 天 → round(上次间隔×EF);
  `is_mastered = repetition >= 5`。前端四档按钮映射 0/2/4/5(见前端 constants)。
- **自测约定**:按契约「打乱后正确答案是 options[0]」实现(判分依据仍记录在库,提交零 LLM 成本)。
  如需改为随机位置,改 `routers/vocabulary.py` 中 `start_quiz` 的 options 组装即可。
- **阅读判分零 LLM 成本**:生成时把 `correct_answer`/`explanation` 落库,提交接口直接判分;
  下发前端的题目中不包含答案字段。
- **CEFR 评分带**:A1=0~39,A2=40~59,B1=60~79,B2=80~89,C1=90~100(契约 3.5 建议)。
- **温度**:对话 0.8、生成类 0.4(契约建议区间内,可在 .env 调整)。

## 冒烟测试

```bash
cd H
# 认证 + 多用户隔离全流程(独立临时库 test_smoke.db,不影响开发库;44 项断言)
..\.venv\Scripts\python tests/auth_smoke.py

# 基础连通性(health 为公开接口)
..\.venv\Scripts\python -c "from fastapi.testclient import TestClient; from app.main import app; print(TestClient(app).get('/api/health').json())"
```
