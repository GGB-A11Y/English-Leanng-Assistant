# 英语学习助手 — 前后端 API 契约

> 本文档是**前端(Vue 3)与后端(LangChain/FastAPI)之间的接口契约**,后端开发者照此实现即可与前端无缝对接。
> 前端代码按本文档约定请求接口,前端仓库中的 `src/api/*` 与此一一对应。

## 1. 通用约定

| 项目 | 约定 |
|---|---|
| 服务地址 | 后端监听 `http://127.0.0.1:8000`;开发环境由前端 Vite dev server 将 `/api/*` 代理到该地址,前端代码中一律使用 `/api` 前缀 |
| 数据格式 | 请求/响应均为 JSON(SSE 接口除外) |
| 时间格式 | ISO 8601 字符串,如 `2026-09-02T10:30:00+08:00` |
| 分页 | 统一响应结构 `{ "items": [], "total": 42, "page": 1, "page_size": 10 }` |
| 错误响应 | 使用 HTTP 状态码 + 统一错误体 `{ "detail": "错误信息" }`(FastAPI 默认行为;422 校验错误的 detail 为数组,前端已做归一化) |
| 生成类接口 | 涉及 LLM 调用的接口(添加单词、翻译、作文批改、生成范文、生成文章)耗时约 10~60s,前端超时设为 **120s**,后端无需特殊处理 |
| CORS | 开发环境经 Vite 代理,无需 CORS;如前端独立部署需自行配置 |
| 鉴权 | 当前无鉴权需求 |

## 2. SSE 流式接口规范(仅 AI 对话使用)

- `POST /api/chat/sessions/{id}/messages` 响应 `Content-Type: text/event-stream`
- **响应体禁止 gzip 压缩**(FastAPI `StreamingResponse` 默认不压缩,请勿加 `GZipMiddleware` 包裹此路由)
- 帧格式:每条消息一行 `data: <JSON>`,以 `\n\n` 结束一帧;可混入以 `:` 开头的注释行作为心跳(如 `: ping`,每 15~30s 一次,防止代理超时)
- 事件类型:
  - `data: {"type":"delta","content":"..."}` — 增量文本,可连续多次
  - `data: {"type":"done","message_id":"...","usage":{"prompt_tokens":123,"completion_tokens":45}}` — 生成完成
  - `data: {"type":"error","message":"..."}` — 生成失败
- 客户端断开连接(如点击"停止生成")时后端应中止 LLM 生成

---

## 3. 接口明细

### 3.1 健康检查

**`GET /api/health`** — 前端每 15s 轮询,用于"后端在线/离线"状态显示

响应:
```json
{ "status": "ok", "version": "0.1.0" }
```

### 3.2 AI 对话

**`POST /api/chat/sessions`** — 创建新会话

响应:
```json
{ "id": "s_1", "title": "新对话", "created_at": "2026-09-02T10:30:00+08:00" }
```

**`GET /api/chat/sessions`** — 会话列表

响应:
```json
[
  { "id": "s_1", "title": "Travel", "created_at": "...", "message_count": 6 }
]
```

**`GET /api/chat/sessions/{id}`** — 会话详情(含历史消息)

响应:
```json
{
  "id": "s_1",
  "title": "Travel",
  "messages": [
    { "id": "m_1", "role": "user", "content": "I go to park yesterday.", "created_at": "..." },
    { "id": "m_2", "role": "assistant", "content": "Great! Just a small correction: ...", "created_at": "..." }
  ]
}
```

**`DELETE /api/chat/sessions/{id}`** — 删除会话 → `{"ok": true}`

**`POST /api/chat/sessions/{id}/messages`** — 发送消息(**SSE**,见第 2 节)

请求:
```json
{ "content": "I like travel very much." }
```
- `content` 非空且 ≤ 4000 字符;客户端断开(停止生成)时后端中止生成并**保留已生成的部分内容**落库

后端职责:
- system prompt 设定"英语对话教练"角色:**全程用英语对话;指出并纠正用户的语法/用词错误;给出更地道的表达;保持友好鼓励的语气**
- 将 user 消息与完整 assistant 回复**落库**,`done` 后 `GET /api/chat/sessions/{id}` 可获取;会话标题可用首条用户消息生成
- 流式输出 assistant 回复(逐 token)

### 3.3 单词学习记忆

**`GET /api/vocabulary/words?page=1&page_size=10&q=apple&group=易错&status=learned`** — 单词列表

- `q` 模糊搜索、`group` 自定义分组名、`status` 学习状态(`learned`=复习过至少一次 / `unlearned`=从未复习),皆可省略,可组合

响应:
```json
{
  "items": [
    {
      "id": "w_1", "word": "apple", "phonetic": "ˈæpl", "pos": "n.",
      "definition_cn": "苹果", "tags": ["水果"], "familiarity": 3,
      "next_review_at": "2026-09-03T09:00:00+08:00", "created_at": "..."
    }
  ],
  "total": 42, "page": 1, "page_size": 10
}
```

**`POST /api/vocabulary/words`** — 添加单词(后端调 LangChain 生成完整词条)

请求:`{"word": "apple"}`(须做 trim/去重校验;**已存在时返回 409** + `{"detail": "单词已存在"}`)

响应(同步返回完整词条):
```json
{
  "id": "w_1", "word": "apple", "phonetic": "ˈæpl", "pos": "n.",
  "definition_cn": "苹果", "definition_en": "a round fruit with red or green skin",
  "examples": [ { "sentence": "She ate an apple.", "translation": "她吃了一个苹果。" } ],
  "roots_affixes": [ { "part": "apple", "meaning": "苹果", "words": ["pineapple"] } ],
  "synonyms": [], "antonyms": [], "collocations": ["apple pie"],
  "tags": [], "note": "", "familiarity": 0, "repetition": 0,
  "next_review_at": null, "created_at": "..."
}
```

**`GET /api/vocabulary/words/{id}`** — 单词详情,响应结构同上(完整词条)

**`POST /api/vocabulary/words/{id}/generate`** — 重新生成 AI 词条详情,响应同完整词条

**`PATCH /api/vocabulary/words/{id}`** — 更新用户自定义字段

请求:`{"tags": ["水果"], "groups": ["易错"], "note": "联想:an apple a day..."}` → 响应完整词条
(注意:重新生成词条时后端会保留学段标签,见 delete_stage)

**`DELETE /api/vocabulary/words/{id}`** → `{"ok": true}`

**内置词库(小学/初中/高中必备词汇,导入零 LLM 成本):**

**`GET /api/vocabulary/builtin`** — 学段列表(含词数与已导入数)

响应:
```json
{
  "stages": [
    { "stage": "primary", "label": "小学必备", "desc": "人教版小学 3~6 年级词汇", "count": 819, "imported": 819 }
  ]
}
```

**`POST /api/vocabulary/words/import`** — 按学段批量导入

请求:`{"stage": "primary"}` → 响应:`{"stage": "primary", "label": "小学必备", "imported": 800, "skipped": 19}`
(已存在的词跳过,词条数据来自内置词库本身,不调 LLM;导入的词带学段标签)

**`DELETE /api/vocabulary/builtin/{stage}`** — 删除已导入的某学段全部单词(按学段标签识别)

响应:`{"ok": true, "deleted": 800, "label": "小学必备"}`

**自定义分组:**

**`GET /api/vocabulary/groups`** → `{"groups": [{"name": "易错", "count": 12}]}`(空分组也保留)

**`POST /api/vocabulary/groups`** — 创建分组,请求 `{"name": "易错"}`
(名称 ≤20 字符;重名 409)→ `{"name": "易错", "count": 0}`

**`DELETE /api/vocabulary/groups/{name}`** — 删除分组(只摘除单词不删词)
→ `{"ok": true, "removed_from": 12}`

**复习(SM-2 间隔重复,由后端实现):**

**`GET /api/vocabulary/review/due?include_new=true&limit=20`** — 到期复习队列

- 到期词(now ≥ next_review_at)优先,不足 `limit` 时按 `include_new` 补从未学过的词(familiarity=0)
- 响应:
```json
{
  "items": [
    { "id": "w_1", "word": "apple", "phonetic": "ˈæpl", "definition_cn": "苹果", "familiarity": 3, "repetition": 2 }
  ],
  "due_count": 5, "total_count": 120
}
```
- `due_count` 为真实到期总数(前端总览页展示),不受 limit 影响

**`POST /api/vocabulary/review/{word_id}`** — 提交复习评分

请求:`{"quality": 4}`(SM-2 质量分 0~5;前端四档按钮映射为 **0/2/4/5**)

后端执行 SM-2 算法(EF 初始 2.5 下限 1.3,**每次评分(含失败)都应用 ΔEF**,quality<3 重置 repetition 且间隔回到 1 天),返回:
```json
{
  "id": "w_1", "familiarity": 4, "repetition": 3,
  "ease_factor": 2.6, "interval_days": 6,
  "next_review_at": "2026-09-08T09:00:00+08:00", "is_mastered": false
}
```

**自测:**

**`GET /api/vocabulary/quiz?count=10`** — 生成自测题(从单词本随机抽词,出中文选项)

```json
{
  "quiz_id": "q_1",
  "questions": [
    { "word": "apple", "phonetic": "ˈæpl", "options": ["苹果", "香蕉", "橘子", "葡萄"] }
  ]
}
```
- **约定:打乱后正确答案是 `options[0]`**,后端需记录每题正确答案以便判分(可落库或内存)

**`POST /api/vocabulary/quiz/{quiz_id}/submit`**

请求:`{"answers": [{"word": "apple", "answer_index": 0}]}`

响应:
```json
{
  "score": 8, "total": 10,
  "results": [
    { "word": "apple", "correct": true, "your_answer": "苹果", "correct_answer": "苹果" },
    { "word": "banana", "correct": false, "your_answer": "橘子", "correct_answer": "香蕉" }
  ]
}
```

### 3.4 英语翻译

**`POST /api/translate`** — 翻译 + 深度解析(同步接口,10~30s;翻译历史由前端本地保存,后端不存)

请求:
```json
{ "text": "这本书对我影响很大。", "source_lang": "zh", "target_lang": "en" }
```
- `text` 非空且 ≤ 2000 字符(对话消息翻译按钮对超长消息会先行提示)
(`source_lang`/`target_lang` 取值 `zh` 或 `en`;前端当前不使用 `auto`,但后端可兼容)

响应:
```json
{
  "translation": "This book has had a great impact on me.",
  "explanation": {
    "phrases": [ { "phrase": "have an impact on", "meaning": "对…有影响", "note": "注意介词搭配 on" } ],
    "grammar_points": [ { "point": "现在完成时", "explanation": "表示过去动作对现在的影响" } ],
    "key_words": [ { "word": "impact", "phonetic": "ˈɪmpækt", "meaning": "影响;冲击" } ],
    "alternatives": ["This book influenced me a lot.", "I was deeply influenced by this book."]
  }
}
```

### 3.5 作文学习

**`GET /api/writing/topics?stage=junior&level=B1&group=考前`** — 题目列表

- `stage` 学段(`primary`/`junior`/`senior`)、`level` CEFR 等级、`group` 自定义分组,皆可省略、可组合
- 内置题库 15 题(启动时按固定 id 补插);排序:内置题按序号,自定义题在后

响应:
```json
{
  "topics": [
    {
      "id": "t_1", "title": "My Favorite Season", "level": "B1", "stage": "junior",
      "prompt": "Write an essay about your favorite season. Describe the weather, activities, and why you like it.",
      "keywords": ["weather", "activities", "feelings"], "groups": []
    }
  ]
}
```

**自定义题目:**

**`POST /api/writing/topics`** — 手动添加,请求 `{"title": "...", "stage": "junior", "prompt": "...", "keywords": ["..."]}`
(title/prompt 非空;标题 ≤80、要求 ≤2000;重名 409)→ 响应完整题目(学段自动映射代表 CEFR 等级:小学 A1/初中 B1/高中 B2)

**`POST /api/writing/topics/parse`** — 批量导入第一步:AI 把粘贴的题目素材整理成规范题目(预览不入库)
请求 `{"text": "…(≤10000 字符)"}` → 响应 `{"topics": [{title, level, prompt, keywords}]}`

**`POST /api/writing/topics/import`** — 批量导入第二步:入库(按标题去重,prompt 为空的跳过)
请求 `{"topics": [...]}` → 响应 `{"imported": 3, "skipped": 1}`

**`PATCH /api/writing/topics/{topic_id}`** — 更新题目自定义字段(当前支持 `groups`)

**`DELETE /api/writing/topics/{topic_id}`** → `{"ok": true}`

**题目分组(与单词分组同模式):**

**`GET /api/writing/groups`** → `{"groups": [{"name": "考前冲刺", "count": 3}]}`

**`POST /api/writing/groups`** 请求 `{"name": "考前冲刺"}`(重名 409)

**`DELETE /api/writing/groups/{name}`** → `{"ok": true, "removed_from": 3}`(只摘除题目不删题)

**`POST /api/writing/essays/grade`** — AI 批改作文(同步,30~60s)

请求:
```json
{
  "topic_id": "t_1",
  "title": "My Favorite Season",
  "content": "I like summer because...",
  "requirement": "请重点检查时态和冠词",
  "stage": "junior"
}
```
(`title`/`requirement` 可空;`topic_id` 可空即自由写作;`stage` 可选,评分参照该学段课程标准;content ≤8000 字符)

响应:
```json
{
  "score": 78,
  "level": "B1",
  "feedback": {
    "overall_comment": "整体结构清晰…(markdown)",
    "strengths": ["开头直接点题", "词汇较丰富"],
    "weaknesses": ["过去时态使用不稳定", "部分句子缺少冠词"],
    "corrections": [
      { "original": "I go to park yesterday.", "corrected": "I went to the park yesterday.", "explanation": "yesterday 提示过去时;park 前需加冠词 the", "type": "grammar" }
    ],
    "vocabulary_suggestions": [
      { "original": "very good", "suggestion": "excellent", "reason": "避免重复使用 very,提升词汇丰富度" }
    ],
    "improved_version": "…(全文润色版,markdown)"
  }
}
```
- `corrections[].type` 取值:`grammar` | `word_choice` | `spelling`
- 评分建议按 CEFR 对应百分制(如 B1: 60~79),`level` 为评估出的当前水平

**`POST /api/writing/essays/sample`** — 按需生成范文(不在 grade 中默认返回以省 token)

请求:`{"topic_id": "t_1"}` → 响应:`{"essay": "…(markdown)"}`

### 3.6 阅读理解

**`POST /api/reading/articles/generate`** — 生成文章 + 题目(同步,20~40s)

请求:`{"stage": "junior", "topic": "technology"}`(`topic` 可空且 ≤100 字符;`level` 旧参数兼容)

- `stage` 学段映射到 CEFR 难度带内随机(小学→A1~A2、初中→A2~B1、高中→B1~B2),增加出题变化

响应:
```json
{
  "article_id": "a_1",
  "title": "The Rise of Smart Homes",
  "level": "B1",
  "stage": "junior",
  "content": "Smart homes are becoming...\n\nAnother benefit is...",
  "word_count": 320,
  "questions": [
    {
      "id": "q_1", "type": "single_choice",
      "question": "What is the main idea of the first paragraph?",
      "options": ["A. Smart homes save energy", "B. Smart homes are expensive", "C. Smart homes use the internet", "D. Smart homes are popular"]
    },
    {
      "id": "q_2", "type": "true_false",
      "question": "Smart homes can be controlled remotely.",
      "options": ["true", "false"]
    }
  ],
  "vocabulary_notes": [ { "word": "remote", "meaning": "远程的" } ]
}
```

**重要设计约定:**
- `single_choice` 为 4 选项,`true_false` 为 2 选项(`"true"`/`"false"`)
- **正确答案与逐题解析由 LLM 在生成时一并产出并由后端存储**(落库或内存均可),提交接口直接判分,**不再调用 LLM**
- 题目须覆盖文章主要内容,难度匹配 CEFR 等级

**`POST /api/reading/articles/{article_id}/submit`** — 提交答案并判分

请求:
```json
{
  "answers": [
    { "question_id": "q_1", "answer": "A. Smart homes save energy" },
    { "question_id": "q_2", "answer": "true" }
  ]
}
```
(**单选题 answer 传完整选项字符串**(如 `"A. Smart homes save energy"`),与生成响应 options 中的元素逐字符一致;判断题 answer 为 `"true"`/`"false"`;未答的题可不传,判为错误)

响应:
```json
{
  "score": 3, "total": 5,
  "results": [
    {
      "question_id": "q_1", "correct": true,
      "your_answer": "A. Smart homes save energy", "correct_answer": "A. Smart homes save energy",
      "explanation": "首段主要讲智能家居的普及…(markdown)"
    }
  ]
}
```

---

## 4. 业务语义说明

| 事项 | 说明 |
|---|---|
| SM-2 quality | 0~5 整数。前端四档按钮 → 0(忘记)/2(困难)/4(良好)/5(简单);**每次评分(含失败)都应用 ΔEF**;quality < 3 时 repetition 重置为 0、间隔回到 1 天;首次成功 1 天 → 第二次 6 天 → 之后 round(上次间隔 × EF);is_mastered = repetition ≥ 5 |
| CEFR 枚举 | `A1` `A2` `B1` `B2` `C1` |
| 学段 stage 枚举 | `primary`(小学)/`junior`(初中)/`senior`(高中);阅读按学段映射 CEFR 难度带随机,作文学段→代表等级 小学 A1/初中 B1/高中 B2 |
| 判断题取值 | `"true"` / `"false"`(字符串) |
| 阅读题正确答案 | 生成时落库的设计意图:提交判分零 LLM 成本、零延迟,且保证判分与题目一致;**单选题提交传完整选项字符串** |
| 单词重复添加 | 409 + `{"detail": "单词已存在"}`;自测题从单词本抽词,单词本至少 4 个词才能开测 |
| 过期数据清理 | 自测记录保留 7 天、阅读文章保留 30 天,启动时自动清理 |

## 5. 存储职责划分

**后端存储(数据库/SQLite 等):**
- 对话会话与消息
- 单词词条 + AI 生成详情(释义/例句/词根词缀等)+ 自定义分组(word_groups)
- 复习状态(SM-2 字段)
- 自测判分所需数据、阅读文章与正确答案
- 作文题库(内置种子 + 自定义题目)与题目分组(topic_groups)

**前端本地存储(localStorage,后端无需实现相关端点):**
- 翻译历史(上限 100 条)
- 作文草稿与批改记录(上限 50 条)
- 阅读理解练习记录(上限 50 条)
- 上次打开的对话会话 ID

## 6. LangChain 实现提示(非强制)

- **结构化输出**:所有生成类接口要求 LLM 返回可解析的 JSON 字段,建议使用 LangChain 的 `with_structured_output` / Pydantic 输出解析器,并在 prompt 中给出 JSON schema 与示例;解析失败时应重试或返回 `{"detail": "生成失败,请重试"}`(5xx 或 4xx)
- **流式对话**:使用 `astream` 逐 token 产出,包装为 SSE 帧(见第 2 节);对话历史(最近 N 轮)放入 prompt 上下文
- **温度建议**:对话 0.7~0.9;词条释义/翻译/批改/文章生成 0.3~0.5(追求稳定)
- 生成类接口建议设置总超时与重试(前端 timeout 为 120s)
