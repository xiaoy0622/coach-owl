# CoachOwl — 执行计划 / Execution Plan v0

> 配套文档：`CoachOwl-PRD-v0.md`（产品需求）
> 本文目标：把 PRD 拆成**可被多个 agent 并行执行**的任务清单 + 编排顺序。
> 状态：草稿 v0 · 工程默认假设已就位（见 §2），可被 Aurora 覆盖。

---

## 0. 如何使用本文档（给编排者 / orchestrator）

- **§1–§6 是"共享契约"**：架构决策、数据模型、API 约定、并行策略。所有 agent 开工前都应读这几节——它们是让前后端、跨模块 agent 不互相踩脚的前提。
- **§7 是任务清单**：每个任务自包含（依赖、可并行项、验收标准、交付文件）。任务 ID 形如 `CO-<stream><nn>`。
- **§8 是执行波次（Waves）**：哪些任务可同时跑、建议派给哪类 agent。
- **并行执行机制建议**：对会**改文件**的实现任务，用 `builder` + `tester-reviewer` 两 agent 配对，或 `general-purpose` agent，并对同一波次内的多个 agent 使用 **git worktree 隔离**（`isolation: "worktree"`）避免写冲突；只读调研用 `Explore`。
- 注意：仓库内置的 `backend-engineer` / `student-frontend` 等子 agent 是 **Cleveroo 仓库专用**（路径绑定 `server/`、`cleveroo-react/`）。CoachOwl 是独立仓库，用通用 agent（`general-purpose` / `builder` / `tester-reviewer`）。

---

## 1. 深度分析（Deep Analysis）

### 1.1 PRD 的核心闭环（MVP 必须打通的一条线）
```
注册/上手  →  建学员（含智能导入）  →  排课（单次/重复 + 冲突检测）
        →  课时包/余额（上一节扣一节 + 低余额提醒）
        →  收款记录 + PDF 发票（可选 GST）
        →  自动提醒（邮件，channel-agnostic）
```
这条线就是 §10 成功指标的载体：**激活率**＝注册后完成"建学员+排第一节课"，所以 onboarding、学员、排课三块是 P0 中的 P0。

### 1.2 三个决定架构的"非功能"约束
1. **Channel-agnostic 通知**：统一 `send()` 接口 + 各通道 adapter，业务逻辑只产生"通知事件"，不关心走邮件还是 SMS。MVP 只实现 EmailAdapter。这是 PRD 反复强调的硬约束。
2. **提醒任务幂等可重试**：靠 `dedupe_key`（如 `lesson:<id>:reminder:24h`）+ 状态机，绝不重复发送。
3. **多租户行级隔离**：单库 + `org_id`（tenant）贯穿所有表 + 应用层强制 scoping（可选 Postgres RLS 兜底）。**所有查询必须带 org_id**——这是安全红线。

### 1.3 本地化（澳洲）贯穿全栈，不能后补
- 货币 **AUD**；**GST 10%** 可开关（org 级）；日期 **DD/MM/YYYY**；时区按 org 设置，默认 **Australia/Sydney**。
- 所有时间**存 UTC、带时区感知**，展示按 org 时区渲染（夏令时 DST 必须正确）。
- 隐私合规（Privacy Act / APPs）：未成年人的 guardian 信息单独标注；数据可导出/删除。

### 1.4 AI 楔子的工程定位
- **智能导入（MVP 首发）**：乱 CSV/粘贴文本 → LLM 抽取 → **用户确认/可编辑** → 落库。复杂度在"解析自由文本重复课程"（"周二周四 4-5pm" → RecurrenceRule）。
- **课后笔记（MVP 轻量）**：文本/语音 → 结构化笔记。语音用本地 faster-whisper（Aurora RTX 3080 Ti）。
- **铁律**：所有 AI 输出**写库前必须有一步人工确认/编辑**，不静默落库。
- LLM 走外部 API（默认 Anthropic Claude，见 §2）。AI 与核心 CRUD 解耦：AI 只产出"候选结构"，落库走与手动相同的 service 层。

### 1.5 风险登记（Top risks）
| 风险 | 影响 | 缓解 |
|------|------|------|
| 重复课程 + DST + 调课的时间模型做错 | 排课全线返工 | §4 数据模型先定稿，写透时区/recurrence 单测 |
| 邮件进垃圾箱 | MVP 唯一触达通道失效 | 事务型服务 + SPF/DKIM/DMARC（CO-N03）早做、早验 |
| 课时余额与扣课/调课不一致 | 对账纠纷（核心痛点） | 余额走**不可变 ledger**，余额=求和派生，绝不就地改数字 |
| AI 抽取错误静默落库 | 用户信任崩塌 | 强制"确认/编辑"中间态（CO-S05 / CO-A02） |
| 多 agent 并行写冲突 | 集成地狱 | 契约先行（§4/§5）+ worktree 隔离 + 模块边界清晰 |

---

## 2. 工程默认假设（解决 PRD §11 开放问题，未定者取工程默认，Aurora 可覆盖）

| PRD 开放问题 | 默认决策（用于排期） | 备注 |
|---|---|---|
| 首发垂直 | **垂直无关的核心**，文案默认偏学科/语言 tutor | 数据模型不锁死垂直 |
| 群课/小班 | **MVP 仅 1:1**；但 `Lesson` 预留 `capacity` 与 `lesson_student` 关联，便于 Phase 2 扩群课 | 不做扣课模型的群课分支 |
| 学员是否登录 | **MVP 只读 magic-link 分享页**，无学员账户 | Should-have，见 CO-W06 |
| 在线收款 | **MVP 仅手动记录**，Stripe 列 Phase 2 | |
| 命名/商标 | 不阻塞工程；并行做商标/域名核查（CO-X05） | |

**技术栈（默认）**
- 后端：**Python 3.12 + FastAPI**，**SQLAlchemy 2.0 + Alembic**，**Pydantic v2**，**PostgreSQL 16**。
- 异步任务：**Redis + ARQ**（轻、单人维护得动；提醒/转写/导入跑后台）。
- 邮件：**Resend**（开发快）或 **AWS SES**（成本低）——抽象在 EmailAdapter 后，二选一不影响业务。默认先接 Resend，留 SES adapter 接口。
- AI：外部 **LLM API（Anthropic Claude，`claude-sonnet-4-6` 抽取/生成）**；语音转写 **faster-whisper 本地**。
- 前端：**React + Vite + TypeScript + Tailwind**，移动端优先响应式；状态用 TanStack Query + 轻量 store。
- 鉴权：邮箱密码 + **JWT**；单 owner 起步，role=`owner|coach`。
- 容器：**docker-compose**（api / worker / postgres / redis）本地一键起；部署目标 Railway 或 Fly.io。
- 测试：后端 **pytest**；前端 **Vitest + Playwright**（关键流程 e2e）。

> 如果 Aurora 想要 Python 全栈（前端也 Python/HTMX）或不同的队列/邮件商，仅影响 CO-F0x 与前端 stream，其余任务契约不变。

---

## 3. 仓库与模块结构（边界＝并行单元）

```
coachowl/
├─ api/                      # FastAPI 后端
│  ├─ app/
│  │  ├─ core/              # config, db, security, tenancy, deps
│  │  ├─ models/            # SQLAlchemy ORM（按域分文件）
│  │  ├─ schemas/           # Pydantic 契约（按域分文件）← 前后端共享契约源
│  │  ├─ services/          # 业务逻辑（CRUD 之上，含 ledger/recurrence）
│  │  ├─ api/v1/            # 路由（按域分文件）
│  │  ├─ notifications/     # channel-agnostic：dispatcher + adapters/
│  │  ├─ ai/                # llm client, import_parser, note_structurer
│  │  └─ workers/           # ARQ 任务：reminders, transcribe, import
│  ├─ alembic/              # 迁移
│  └─ tests/
├─ web/                      # React + Vite 前端
│  └─ src/{api,components,features,pages,lib}/
├─ docs/                     # 架构、数据模型、契约
├─ docker-compose.yml
└─ CoachOwl-PRD-v0.md / CoachOwl-Execution-Plan-v0.md
```

**模块（domain）边界**——每个域是一个相对独立的并行 stream，包含 model + schema + service + route（+ 对应前端 feature）：
`auth/org` · `students` · `scheduling` · `credits` · `payments/invoices` · `notifications` · `ai` · `web-shell`。

---

## 4. 共享数据模型（契约 v0 —— 所有 agent 以此为准）

> 所有表含 `id (uuid)`、`org_id (uuid, FK organizations)`、`created_at`、`updated_at`。**org_id 强制索引并参与每个查询**。

- **organizations**（tenant）：`name, timezone='Australia/Sydney', currency='AUD', gst_enabled bool, gst_rate=0.10, abn?, brand_name`
- **users**：`org_id, email(unique), password_hash, name, role(owner|coach), is_active`
- **students**：`org_id, name, email?, phone?, status(active|paused|churned), tags text[], notes?`
- **guardians**：`org_id, student_id, name, relationship, email?, phone?, is_primary`（未成年人）
- **recurrence_rules**：`org_id, freq(weekly), interval=1, byweekday int[], start_date, end_date?, start_time, duration_min`
- **lessons**（session）：`org_id, student_id, coach_id(users), recurrence_id?, starts_at(tz-aware UTC), duration_min, status(scheduled|completed|cancelled|no_show), location?, meeting_url?, cancel_reason?, credit_deducted bool` ·（预留 `capacity=1` 供群课）
- **credit_packs**：`org_id, student_id, name, total_sessions, price_per_session(numeric), purchased_at, expires_at?`
- **credit_ledger**（不可变）：`org_id, student_id, pack_id?, lesson_id?, delta int(+/-), reason(purchase|deduct|refund|adjust), created_at` ·**余额 = SUM(delta)，绝不就地改**
- **payments**：`org_id, student_id, amount(numeric), method(cash|transfer|other), pack_id?, paid_at, note?, status(paid|due)`
- **invoices**：`org_id, student_id, number(seq/org), line_items(jsonb), subtotal, gst_amount, total, status(draft|sent|paid), pdf_url?, issued_at`
- **notifications**（log/outbox）：`org_id, channel(email), template, recipient, payload(jsonb), dedupe_key(unique), status(pending|sent|failed), scheduled_for, sent_at?, error?`
- **lesson_notes**：`org_id, lesson_id, student_id, raw_input, structured(jsonb: topics/progress/homework), source(text|voice), audio_url?`
- **share_links**：`org_id, student_id, token(unique), expires_at?`（只读课表）
- **import_jobs**：`org_id, raw_input, parsed(jsonb 候选), status(parsing|review|committed|discarded)`（智能导入的"确认/编辑"中间态）

**关键不变式（写进单测）**
1. 任意时刻 `student balance = SUM(credit_ledger.delta where student)`。
2. `lesson.status=completed` ⇒ 恰好一条 `delta=-1` 的 ledger（除非课时包关闭扣课）。
3. 同一 `dedupe_key` 的 notification 至多发送一次。
4. 所有列表/详情查询都带 `WHERE org_id=:current_org`。

---

## 5. API 与协作约定（让前后端并行）

- **契约先行**：每个域先在 `api/app/schemas/<域>.py`（Pydantic）定义 Request/Response，并由 FastAPI 自动产出 **OpenAPI**。前端从 OpenAPI 生成/手写 TS 类型，**对着契约写，不等后端实现**。
- 路由前缀 `/api/v1/<域>`；统一分页 `?limit&cursor`；统一错误体 `{error:{code,message,details?}}`。
- 鉴权：`Authorization: Bearer <jwt>`；依赖注入 `current_user` / `current_org`，所有受保护路由强制注入 `org_id`。
- 时间：API 一律 **ISO8601 UTC**；前端按 org timezone 渲染。金额：**字符串化的 decimal**，避免浮点。
- 提交规范：`CO-<id> <message>`（呼应任务 ID，便于回溯）。

---

## 6. 并行化策略（核心）

**三层让出并行度：**
1. **契约层先冻结**（Wave 0–1）：数据模型（§4）、Pydantic schemas、OpenAPI。一旦冻结，下游 agent 互不阻塞。
2. **按域水平切分**（Wave 2+）：students / scheduling / credits / payments / notifications / ai 各自一个 backend agent，互相只通过 service 接口与 schema 交互。
3. **前后端垂直切分**：同一域内，backend agent 实现路由、frontend agent 对着 OpenAPI 实现页面，二者并行；用 `tester-reviewer` 对契约写 e2e 兜底。

**冲突规避**：每个并行 agent 限定在自己的目录子树（`models/<域>.py`、`api/v1/<域>.py`、`web/src/features/<域>/`）。共享文件（`models/__init__`、路由注册、`db` 基类）在 Wave 0/1 一次性建好，后续尽量 append-only。改共享文件的任务排成串行或用 worktree+人工合并。

---

## 7. 任务清单（Task Breakdown）

> 字段：**Stream**｜**Depends**（前置）｜**Parallel**（可同时跑）｜**Agent**（建议类型）｜**AC**（验收标准）。
> Stream 代码：F=Foundation、S=Students、C=Calendar/Scheduling、K=Credits、P=Payments/Invoices、N=Notifications、A=AI、W=Web、X=Cross-cutting。

### Stream F — Foundation（基础设施，多为前置，尽量早做）

**CO-F01 — 仓库脚手架与 docker-compose**
- Depends: 无 ｜ Parallel: CO-F02, CO-W01 ｜ Agent: general-purpose
- 描述：建 `api/`（FastAPI app factory、settings via pydantic-settings、健康检查 `/api/health`）、`web/`（Vite+TS+Tailwind 空壳）、`docker-compose.yml`（api/worker/postgres/redis）、`.env.example`、README 启动说明。
- AC：`docker compose up` 后 `GET /api/health` 返回 200；`web` 本地起得来；CI lint/format（ruff + black + eslint）配好。

**CO-F02 — DB 基座、迁移与多租户骨架**
- Depends: CO-F01 ｜ Parallel: CO-F03 ｜ Agent: general-purpose（backend）
- 描述：SQLAlchemy 2.0 base、session、Alembic 初始化；实现 `organizations` + `users` 表与基础 mixin（id/org_id/timestamps）；应用层 tenancy 依赖（`current_org`），可选 Postgres RLS 策略脚本。
- AC：`alembic upgrade head` 成功建表；写一个 `tenant_scope` 依赖与单测证明跨租户查询被挡。

**CO-F03 — 鉴权与 onboarding 后端（注册/登录/JWT/org 设置）**
- Depends: CO-F02 ｜ Parallel: CO-F04 ｜ Agent: builder + tester-reviewer
- 描述：`/api/v1/auth/register|login|me`；注册即建 org + owner user；org 设置端点（timezone/currency/gst）。密码 hash（argon2/bcrypt）。
- AC：注册→登录→`/me` 全链路绿；JWT 校验中间件；pytest 覆盖正/反例。

**CO-F04 — §4 全量数据模型 + 迁移（一次性建表）**
- Depends: CO-F02 ｜ Parallel: CO-F03 ｜ Agent: builder + tester-reviewer
- 描述：把 §4 所有实体落成 ORM models + 一个 Alembic 迁移（students/guardians/recurrence/lessons/credit_packs/credit_ledger/payments/invoices/notifications/lesson_notes/share_links/import_jobs）。**仅建表与约束/索引，不写业务逻辑**。
- AC：`alembic upgrade head/downgrade base` 双向通过；所有表带 `org_id` 索引；外键/枚举/唯一约束（含 `notifications.dedupe_key`）就位。**这是 Wave 2 大并行的总闸门。**

**CO-F05 — 共享 Pydantic schemas（全域契约）**
- Depends: CO-F04 ｜ Parallel: CO-W02 ｜ Agent: general-purpose
- 描述：为每个域写 `schemas/<域>.py` 的 Request/Response（即使 service 未实现）。导出 OpenAPI JSON 到 `docs/openapi.json`。
- AC：`uvicorn` 启动后 `/docs` 列出所有域的 schema；OpenAPI 导出成功，供前端消费。

### Stream S — Students / CRM（含智能导入接入点）

**CO-S01 — 学员 CRUD API**
- Depends: CO-F04, CO-F05 ｜ Parallel: 各 Stream 首任务 ｜ Agent: builder + tester-reviewer
- AC：`/api/v1/students` 增删改查 + 状态(active/paused/churned) + tags + 搜索/分页；全部 org-scoped；pytest 覆盖跨租户隔离。

**CO-S02 — 监护人(guardian)与未成年标注**
- Depends: CO-S01 ｜ Parallel: CO-S03 ｜ Agent: general-purpose
- AC：学员可挂多个 guardian，标 `is_primary`；未成年学员要求至少一个 primary guardian（校验）。

**CO-S03 — 学员前端：列表 + 档案页**
- Depends: CO-F05（契约）, CO-W02（shell）｜ Parallel: CO-S01（对契约并行）｜ Agent: general-purpose（frontend）
- AC：列表（搜索/筛状态/tag）、详情、增改表单；移动端优先；空态/加载/错误态完整。URL 可寻址（`/students`、`/students/:id`）。

**CO-S04 — 智能导入后端：解析端点 + import_jobs 状态机**
- Depends: CO-S01, CO-A01 ｜ Parallel: CO-S05 ｜ Agent: builder + tester-reviewer
- 描述：`POST /students/import/parse`（吃 CSV/粘贴文本 → 调 §A LLM parser → 存 `import_jobs.parsed` 候选，status=review）；`POST /students/import/:job/commit`（用户确认后的结构 → 批量建学员/recurrence）。
- AC：乱列序/姓名电话混排/"周二周四4-5pm"自由文本能解析成候选；commit 落库走与手动相同的 service；解析失败有兜底（逐行回退人工映射）。

**CO-S05 — 智能导入前端：上传 → 候选预览 → 编辑确认 → 提交**
- Depends: CO-S04（契约）, CO-S03 ｜ Parallel: CO-S04 ｜ Agent: general-purpose（frontend）
- AC：粘贴/上传 → 表格化候选（字段映射可改、行可删/编辑）→ 提交建档；**确认前不落库**（呼应 §1.4 铁律）；显示解析置信度/告警。

### Stream C — Scheduling / Calendar（时间模型，最高风险）

**CO-C01 — Recurrence 引擎 + 时区/DST 工具（纯逻辑，先行）**
- Depends: CO-F04 ｜ Parallel: CO-C02 ｜ Agent: builder + tester-reviewer
- 描述：把 RecurrenceRule 展开为具体 lesson occurrences 的纯函数；统一 UTC 存储、org tz 渲染；DST 边界正确。
- AC：单测覆盖跨夏令时切换、每周多天、interval、end_date；为后续排课提供可信底座。

**CO-C02 — 课程(lesson) CRUD + 冲突检测 API**
- Depends: CO-F04, CO-C01 ｜ Parallel: CO-C03 ｜ Agent: builder + tester-reviewer
- AC：单次/重复创建（重复经 CO-C01 展开）；同一 coach 时间重叠检测；`/api/v1/lessons?from&to` 周/月查询；org-scoped。

**CO-C03 — 调课 / 请假 / 取消（含扣课时联动钩子）**
- Depends: CO-C02, CO-K01 ｜ Parallel: CO-C04 ｜ Agent: builder + tester-reviewer
- 描述：改时间、标记 no_show/cancelled、记录原因；可选是否扣课时（调用 Credits service，不直接改 ledger 数字）；产生通知事件（调用 Notifications dispatcher）。
- AC：状态机合法迁移；扣课与否都正确反映在余额；取消产生一条 notification（dedupe）。

**CO-C04 — 日历前端：周/月视图 + 排课/调课交互**
- Depends: CO-F05, CO-W02 ｜ Parallel: CO-C02（对契约并行）｜ Agent: general-purpose（frontend）
- AC：周/月视图，点开课程做调课/请假/取消；冲突高亮；移动端友好；URL 含视图与日期（`/calendar?view=week&date=...`）。

### Stream K — Credits / Packages（课时包与余额，走不可变 ledger）

**CO-K01 — 课时包 + Ledger service（余额=派生）**
- Depends: CO-F04 ｜ Parallel: CO-C01 ｜ Agent: builder + tester-reviewer
- 描述：买包（写 +N ledger）、扣课（-1）、退/调整；`get_balance(student)=SUM(delta)`；**杜绝就地改余额**。
- AC：§4 不变式 1/2 的单测全绿；并发扣课不超扣（行锁/事务）；低余额阈值可配。

**CO-K02 — 课时包前端 + 余额展示**
- Depends: CO-F05, CO-W02, CO-S03 ｜ Parallel: CO-K01 ｜ Agent: general-purpose（frontend）
- AC：学员档案页显示当前余额、购买记录、扣课流水；买包表单；低余额视觉提示。

**CO-K03 — 低余额提醒触发器**
- Depends: CO-K01, CO-N01 ｜ Parallel: 其它 ｜ Agent: general-purpose
- AC：余额 ≤ 阈值时产生一条 notification 事件（经 dispatcher，dedupe，按 student/阈值幂等）。

### Stream P — Payments / Invoices

**CO-P01 — 收款记录 API + 收入概览**
- Depends: CO-F04 ｜ Parallel: 其它 ｜ Agent: builder + tester-reviewer
- AC：记录付款（cash/transfer/other，挂 pack 或单次）；本月已收/待收聚合端点；org-scoped。

**CO-P02 — 发票生成 + PDF（可选 GST 10%）**
- Depends: CO-P01 ｜ Parallel: CO-P03 ｜ Agent: builder + tester-reviewer
- 描述：按 org `gst_enabled` 计算 subtotal/gst/total；生成 PDF（WeasyPrint/ReportLab）；org 内发票号自增。
- AC：GST 开/关两种发票数额正确；PDF 渲染含 ABN/品牌名；DD/MM/YYYY、AUD 格式。

**CO-P03 — 收款/发票前端 + 月底对账视图**
- Depends: CO-F05, CO-W02 ｜ Parallel: CO-P01 ｜ Agent: general-purpose（frontend）
- AC：收入概览（已收/待收）、记一笔付款、生成/下载发票、对未付学员一键发提醒（呼应流程 C）。

### Stream N — Notifications（channel-agnostic，PRD 硬约束）

**CO-N01 — 通知抽象层：Dispatcher + EventBus + Outbox**
- Depends: CO-F04 ｜ Parallel: CO-N02 ｜ Agent: builder + tester-reviewer
- 描述：统一 `notify(event, recipient, template, payload, dedupe_key, scheduled_for)`；写 `notifications`(outbox)；adapter 注册表（channel→adapter）。业务侧只调 dispatcher。
- AC：dedupe_key 唯一性保证不重复；adapter 接口定义清晰；EmailAdapter 之外可注册 mock/sms 占位。

**CO-N02 — EmailAdapter（Resend，SES 接口预留）+ 模板**
- Depends: CO-N01 ｜ Parallel: CO-N03 ｜ Agent: general-purpose
- AC：课前提醒/低余额/发票/调课模板；发送结果回写 outbox 状态；失败重试。可切 SES（同接口）。

**CO-N03 — 邮件可达性（SPF/DKIM/DMARC）配置与文档**
- Depends: CO-N02 ｜ Parallel: 其它 ｜ Agent: general-purpose
- AC：域名 DNS 记录清单 + 验证步骤文档；测试邮件不进垃圾箱（人工验一次）。**MVP 唯一触达通道，必须做。**

**CO-N04 — 提醒调度 worker（ARQ，幂等可重试）**
- Depends: CO-N01, CO-C02 ｜ Parallel: CO-N02 ｜ Agent: builder + tester-reviewer
- 描述：定时扫描即将开始的课，按 `lesson:<id>:reminder:<offset>` 生成提醒；outbox 消费者发送；崩溃可重试不重发。
- AC：重复运行不产生重复发送（dedupe）；偏移量（如 24h/1h）可配；时区正确。

### Stream A — AI（智能导入解析 + 课后笔记）

**CO-A01 — LLM 客户端 + 智能导入解析器**
- Depends: CO-F01 ｜ Parallel: CO-A02 ｜ Agent: builder + tester-reviewer
- 描述：封装外部 LLM（Anthropic Claude `claude-sonnet-4-6`）；`parse_import(raw)→候选结构`（字段识别、姓名/联系方式/家长拆分、自由文本重复课程→RecurrenceRule 草案）。带 schema 校验 + 失败回退。
- AC：给定脏样本输出结构化候选 JSON（贴合 §4）；prompt/版本与成本可观测；离线 fixtures 测试（不真打 API 也能跑）。

**CO-A02 — 课后笔记结构化（文本）+ 笔记 API**
- Depends: CO-F04, CO-A01 ｜ Parallel: CO-C02 ｜ Agent: builder + tester-reviewer
- 描述：`lesson_notes` CRUD；`structure_note(raw)→{topics,progress,homework}`；写库前返回候选供前端编辑确认。
- AC：文本输入产出结构化笔记候选；确认后落库；跨课可按 topic 追踪。

**CO-A03 — 语音笔记：faster-whisper 转写 worker（MVP 轻量，可后置）**
- Depends: CO-A02, CO-N01(worker 基础) ｜ Parallel: 其它 ｜ Agent: general-purpose
- AC：上传音频 → ARQ 任务 → 本地 faster-whisper 转写 → 交 CO-A02 结构化 → 候选待确认。失败可重试。
- 备注：若 GPU/转写环境未就绪，可标记为 Wave 4 / Phase 后置，不阻塞 MVP 闭环。

**CO-A04 — 笔记前端：录入/语音 → 候选编辑 → 保存**
- Depends: CO-A02（契约）, CO-W02, CO-C04 ｜ Parallel: CO-A02 ｜ Agent: general-purpose（frontend）
- AC：每节课一条笔记；文本/语音入口；AI 候选可编辑后保存（呼应确认铁律）。

### Stream W — Web shell / Onboarding / Dashboard

**CO-W01 — 前端脚手架 + 路由 + 设计系统底座**
- Depends: CO-F01 ｜ Parallel: CO-F02 ｜ Agent: general-purpose（frontend）
- AC：Vite+TS+Tailwind；React Router（每屏一路由，URL 可寻址）；TanStack Query；API client（注入 JWT）；基础组件（按钮/表单/表格/空态/toast）。

**CO-W02 — 应用外壳：登录页 + 受保护布局 + 导航**
- Depends: CO-W01, CO-F03（契约）｜ Parallel: CO-F05 ｜ Agent: general-purpose（frontend）
- AC：登录/注册页对接 auth；登录后布局（侧栏/底部 tab 移动端）；未登录重定向；org 设置页（tz/currency/GST）。

**CO-W03 — 引导式 onboarding（建首个学员 → 排首节课）**
- Depends: CO-W02, CO-S03, CO-C04 ｜ Parallel: 其它前端 ｜ Agent: general-purpose（frontend）
- AC：新用户 10 分钟内走完"注册→设置→建学员→排第一节课"；这是激活率指标载体；步骤可跳过/续接。

**CO-W04 — Dashboard（今日课程 + 收入概览 + 待办提醒）**
- Depends: CO-W02, CO-C02, CO-P01 ｜ Parallel: 其它 ｜ Agent: general-purpose（frontend）
- AC：首屏聚合今日/本周课程、本月已收/待收、低余额/未付提醒入口。

**CO-W05 — 上课记录/进度笔记列表（Should）**
- Depends: CO-A04 ｜ Parallel: 其它 ｜ Agent: general-purpose（frontend）
- AC：按学员看历次笔记时间线。

**CO-W06 — 学员/家长只读课表分享页（Should，免登录 token）**
- Depends: CO-F04(share_links), CO-C02 ｜ Parallel: 其它 ｜ Agent: builder + tester-reviewer（全栈小任务）
- AC：`/share/:token` 免登录展示某学员课表 + 余额；token 可过期/吊销；不泄露其它学员数据。

### Stream X — Cross-cutting（贯穿，部分可早做/并行）

**CO-X01 — 本地化工具（AUD/GST/DD-MM-YYYY/timezone）前后端共用**
- Depends: CO-F02 ｜ Parallel: 早期各任务 ｜ Agent: general-purpose
- AC：后端金额/日期/税 util + 前端 formatter（Intl，locale en-AU）；被各域复用，单测覆盖 DST 与 GST 计算。

**CO-X02 — 测试与 CI 流水线**
- Depends: CO-F01 ｜ Parallel: 持续 ｜ Agent: qa/general-purpose
- AC：GitHub Actions：后端 pytest + ruff、前端 vitest + eslint + build；关键 e2e（注册→建学员→排课→提醒）Playwright；PR 必过。

**CO-X03 — 合规：数据导出/删除 + 隐私文档（APPs）**
- Depends: CO-F04 ｜ Parallel: 后期 ｜ Agent: general-purpose
- AC：账户数据导出（JSON/CSV）与硬删除端点；未成年人 guardian 信息标注；隐私政策草稿。

**CO-X04 — 可观测性与错误处理基线**
- Depends: CO-F01 ｜ Parallel: 持续 ｜ Agent: general-purpose
- AC：结构化日志、请求 id、统一异常处理、AI/邮件调用的成本与失败计数埋点。

**CO-X05 — 商标/域名核查（非工程，可并行外包给调研 agent）**
- Depends: 无 ｜ Parallel: 全程 ｜ Agent: general-purpose / Explore + WebSearch
- AC：CoachOwl 澳洲商标（IP Australia）+ 域名（coachowl.com/.com.au）可用性报告；给出备选名。

---

## 8. 执行波次（Waves）与 agent 编排

> 同一波内的任务可并行派给不同 agent；跨波有依赖。建议每波 fan-out 后由 orchestrator 收口、合并、跑 CI 再进下一波。

**Wave 0 — 地基（少量串行，尽快完成）**
- CO-F01（脚手架）→ 解锁几乎一切
- 并行起步：CO-X05（调研，纯并行）、CO-W01（前端脚手架，依赖 F01）
- Agent：1× general-purpose 起 F01；F01 完成后 W01 与 X05 并行。

**Wave 1 — 契约冻结（关键并行闸门前）**
- 并行：CO-F02（DB/tenancy）、CO-X01（本地化）、CO-X02（CI）、CO-X04（可观测）
- 串行紧随：CO-F03（auth）∥ CO-F04（全量建表）；CO-F04 是 Wave 2 总闸门
- 然后 CO-F05（schemas/OpenAPI）∥ CO-W02（app shell）
- Agent：3–4× 并行（builder+tester 配对用于 F03/F04）。

**Wave 2 — 域大并行（契约就绪后火力全开）**
- 后端域并行：CO-S01、CO-C01→CO-C02、CO-K01、CO-P01、CO-N01、CO-A01
- 前端域并行（对 OpenAPI 契约）：CO-S03、CO-C04、CO-K02、CO-P03、CO-W03、CO-W04
- Agent：6–10× 并行；**强烈建议 worktree 隔离**；每个 agent 限定自己域的目录子树。

**Wave 3 — 联动与 AI 楔子（依赖 Wave 2 的 service）**
- CO-C03（调课↔扣课↔通知）、CO-K03（低余额提醒）、CO-N02/N04（邮件+提醒 worker）、CO-S04/S05（智能导入全链）、CO-A02/A04（笔记）、CO-P02（发票 PDF）、CO-S02（guardian）
- Agent：5–8× 并行。

**Wave 4 — Should-have + 合规 + 硬化**
- CO-N03（邮件可达性）、CO-W05、CO-W06（分享页）、CO-A03（语音转写）、CO-X03（合规导出/删除）、端到端 e2e 强化、性能与安全自查。

**冲突治理**：跨波改共享文件（路由注册、`models/__init__`、`schemas` 汇总、前端路由表）的改动，集中在 Wave 1 一次建好，Wave 2+ 尽量 append-only；必要时该类合并由 orchestrator 串行处理。

---

## 9. MVP 完成判据（Definition of Done）

闭环可演示：**注册 → 设置 org（tz/AUD/GST）→ 智能导入或手动建学员 → 排重复课（DST 正确，冲突检测）→ 买课时包、上课扣课、低余额提醒 → 记录收款、出 GST 发票 PDF → 课前邮件提醒（幂等，不进垃圾箱）→ 课后结构化笔记**。
- §4 全部不变式单测绿；跨租户隔离测试绿；关键流程 Playwright e2e 绿。
- 激活流程（建学员+排首课）可在 10 分钟内完成（呼应 §10 激活率）。

## 10. 待 Aurora 确认（影响排期的决策点）
1. 技术栈是否采纳 §2 默认（FastAPI/Postgres/ARQ/Resend/React）。
2. 首发垂直 & 是否 MVP 就要群课（默认 1:1，预留扩展）。
3. 邮件商 Resend vs SES（默认 Resend，接口已抽象）。
4. 部署目标（Railway vs Fly）。
5. 语音笔记（CO-A03）放 MVP 还是后置（默认轻量后置，不阻塞闭环）。

---
*本计划随 PRD 收敛到 v1 后同步更新；任务 ID 稳定，便于 commit 前缀与 agent 派单引用。*
