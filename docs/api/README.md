# 接口契约（API Contract）

> 契约先行：前后端据此并行开发。后端以 FastAPI 自动生成的 OpenAPI（`/docs`、`/openapi.json`）为准，本目录记录约定与草案。

## 约定

- 风格：REST + JSON，资源命名用复数名词。
- 鉴权：`Authorization: Bearer <access_token>`。
- 统一响应：成功返回资源体；错误返回 `{ "detail": "<message>" }` + 合适的 HTTP 状态码。
- 分页：`?page=&size=`，响应含 `items` 与 `total`。
- 时间：ISO 8601（UTC）。

## 资源草案（随实现细化）

### 认证 `auth`
- `POST /auth/register` — 注册（email, password, nickname）
- `POST /auth/login` — 登录，返回 access + refresh token
- `POST /auth/refresh` — 刷新 token
- `GET  /users/me` — 当前用户信息（含积分余额）

### 分类 `catalog`
- `GET /categories?section=` — 按板块获取分类树

### 内容
- `GET /knowledge`, `GET /knowledge/{id}`
- `GET /sql-questions`, `GET /sql-questions/{id}`
- `GET /companies`, `GET /companies/{id}/interviews`
- `GET /projects`, `GET /projects/{id}`（付费内容需 entitlement）

### 投稿 `submissions`
- `POST /submissions` — 提交原始内容（触发 LLM 加工任务）
- `GET  /submissions/me` — 我的投稿及状态

### 积分 `points`
- `GET /points/ledger` — 我的积分账本

### 支付 / 解锁 `payment`
- `POST /orders` — 现金下单（Mock）
- `POST /redemptions` — 积分兑换解锁
- `GET  /entitlements/me` — 我的已解锁内容

### 管理后台 `admin`（role=admin）
- `GET  /admin/submissions?status=pending_review` — 审核队列
- `POST /admin/submissions/{id}/approve` — 通过并发布（发放积分）
- `POST /admin/submissions/{id}/reject` — 退回
- `CRUD /admin/categories`, `/admin/knowledge`, `/admin/projects` ...

> 以上为草案，字段级细节在实现 PR 中同步到本文件或直接以 OpenAPI 为准。
