# 技术架构

> 状态：定稿 v1.0 · 随实现演进通过 PR 更新

## 1. 总览

```
┌─────────────┐        HTTPS/JSON        ┌──────────────────┐
│  Next.js    │  ───────────────────▶   │   FastAPI API     │
│  (Vercel)   │  ◀───────────────────   │  (Render/Railway) │
└─────────────┘        OpenAPI           └───────┬──────────┘
                                                  │
                     ┌────────────────────────────┼───────────────┐
                     ▼                             ▼               ▼
              ┌────────────┐              ┌───────────────┐  ┌──────────┐
              │ PostgreSQL │              │  Redis (ARQ)  │  │  豆包 Ark │
              │  (Neon)    │              │  (Upstash)    │  │  LLM     │
              └────────────┘              └───────┬───────┘  └──────────┘
                                                  │
                                          ┌───────▼────────┐
                                          │  ARQ Worker    │
                                          │ (LLM 加工任务) │
                                          └────────────────┘
```

## 2. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 前端 | Next.js (App Router, TS) + Tailwind + shadcn/ui | 现代简洁 UI，SSR/SEO 友好，Vercel 部署顺滑 |
| 后端 | FastAPI（模块化单体） | 异步友好，利于 LLM 调用；自动 OpenAPI；早期简单、可平滑拆分 |
| ORM / 迁移 | SQLAlchemy 2.x + Alembic | 成熟、类型友好 |
| 数据库 | PostgreSQL（Neon） | 关系型，托管省运维 |
| 异步队列 | ARQ + Redis（Upstash） | asyncio 原生，轻量，扩展性好 |
| 鉴权 | JWT（access + refresh）+ bcrypt | 无状态、前后端分离友好 |
| 大模型 | 豆包（Ark, OpenAI 兼容） | 默认提供商；抽象层可切换 |
| 支付 | 抽象 Provider + Mock | 骨架先行，通道后置 |

## 3. 后端分层

每个业务模块内部遵循统一分层：

```
router (HTTP、请求校验、依赖注入)
   │
service (业务逻辑、事务边界、跨模块编排)
   │
repository (数据访问，隔离 ORM 细节)
   │
model (SQLAlchemy ORM 实体)
```

跨模块调用**只允许经由 service 接口**，不得跨模块直接访问对方的 repository / model。

## 4. 目录结构（后端）

```
backend/
  app/
    core/            # 配置、鉴权、依赖、异常、日志、DB/Redis 会话
    modules/
      auth/          # 注册、登录、JWT、角色
      users/         # 用户资料
      points/        # 积分账本、发放/消耗（幂等）
      catalog/       # 分类树（四大 section 共用）
      knowledge/     # 八股
      sql_bank/      # SQL 题库
      interview/     # 面经（按企业）
      projects/      # 项目（免费/付费/QA）
      submissions/   # 用户投稿 + 审核状态机
      llm/           # LLMClient 抽象 + DoubaoClient + MockLLM
      payment/       # PaymentProvider 抽象 + MockProvider + 订单/entitlement
      admin/         # 后台聚合接口
    workers/         # ARQ 任务（LLM 加工）
    main.py
  alembic/           # 迁移
  tests/
  pyproject.toml
```

## 5. 可插拔接口（扩展性关键）

```python
class LLMClient(Protocol):
    async def format_content(self, raw: str, template: str) -> str: ...
# 实现：DoubaoClient / MockLLM，按 LLM_PROVIDER env 切换

class PaymentProvider(Protocol):
    async def create_order(self, order) -> PaymentIntent: ...
    async def verify(self, ref) -> PaymentResult: ...
    async def refund(self, ref) -> RefundResult: ...
# 实现：MockProvider（现在）→ WechatProvider / AlipayProvider / StripeProvider（后续，零改调用方）

class Storage(Protocol):
    async def save(self, key, data) -> str: ...
# 附件/图片，先本地实现，后接对象存储
```

## 6. 数据模型（核心实体）

| 表 | 关键字段 |
|---|---|
| `user` | id, email(uniq), password_hash, nickname, role, points_balance, created_at |
| `point_ledger` | id, user_id, delta, reason, ref_type, ref_id, created_at（发放幂等以 ref 去重） |
| `category` | id, parent_id, section, name, slug, order（邻接表，无限下钻）|
| `knowledge_item` | id, category_id, title, content_md, is_paid, price_cash, price_points, status, author_id |
| `sql_question` | id, category_id, title, difficulty, prompt_md, answer_md, tags, status, author_id |
| `company` | id, name, logo_url |
| `interview_post` | id, company_id, position, content_md, status, author_id |
| `project` | id, title, description_md, implementation_md, level, access_type, price_cash, price_points, status, author_id |
| `project_qa` | id, project_id, question_md, answer_md, order |
| `submission` | id, user_id, target_type, raw_content, processed_md, status, reject_reason, created_at |
| `order` | id, user_id, item_type, item_id, amount_cash, status, provider, created_at |
| `entitlement` | id, user_id, content_type, content_id, source（purchase/points）|

`section ∈ {knowledge, sql, interview, project}`
`status ∈ {draft, processing, pending_review, published, rejected}`

## 7. 部署形态

| 组件 | 平台 |
|---|---|
| 前端 | Vercel |
| 后端 API | Render / Railway（常驻进程） |
| Worker | Render / Railway（独立进程） |
| PostgreSQL | Neon |
| Redis | Upstash |

本地开发：`infra/docker-compose.yml` 起 Postgres + Redis，后端与前端本地运行。全部配置走环境变量（见 `.env.example`）。

## 8. 契约先行

- 后端通过 FastAPI 自动生成 OpenAPI（`/docs`）。
- 接口约定沉淀在 [api/README.md](api/README.md)，前端可据此用 mock 并行开发。
