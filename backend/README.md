# backend · FastAPI

数据开发学习 & 面试平台后端。模块化单体，分层 `router → service → repository → model`。

## 环境要求

- Python 3.11+
- Postgres + Redis（本地用 `infra/docker-compose.yml`）

## 快速开始

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 准备环境变量（在仓库根目录复制 .env.example 为 .env，或导出环境变量）
cp ../.env.example .env

# 启动依赖（在仓库根目录）
docker compose -f ../infra/docker-compose.yml up -d

# 建表
alembic upgrade head

# 灌入种子数据（含管理员 admin@example.com / admin12345）
python -m scripts.seed

# 启动 API（http://localhost:8000，文档 /docs）
uvicorn app.main:app --reload
```

### 无 Docker 快速演示（SQLite）

M0–M2 不依赖 Redis（投稿默认同步加工），可用 SQLite 直接跑：

```bash
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
alembic upgrade head && python -m scripts.seed
uvicorn app.main:app --reload
```

### 投稿异步加工（生产，可选）

设置 `TASK_QUEUE_ENABLED=true` 后，投稿加工进入 ARQ 队列，需另起 Worker：

```bash
arq app.workers.main.WorkerSettings
```

## 常用命令

```bash
pytest            # 测试（使用内存 sqlite，无需 Postgres）
ruff check .      # lint
ruff format .     # 格式化
mypy app          # 类型检查
alembic revision -m "msg"   # 新建迁移
alembic upgrade head        # 应用迁移
```

## 目录

```
app/
  core/       # 配置、DB、鉴权、依赖
  modules/
    auth/     # 注册/登录/JWT
    users/    # 用户模型与 /users/me
alembic/      # 迁移
tests/        # pytest（sqlite 内存库）
```

## 已实现

### M0 · 鉴权
- 健康检查 `GET /health`
- 注册 / 登录 / 刷新 `POST /auth/register|login|refresh`
- 当前用户 `GET /users/me`（需 Bearer token）

### M1 · 内容浏览（只读）
- 分类树 `GET /categories?section=`
- 八股 `GET /knowledge`、`GET /knowledge/{id}`
- SQL `GET /sql-questions`、`GET /sql-questions/{id}`
- 面经 `GET /companies`、`GET /companies/{id}/interviews`、`GET /interviews/{id}`
- 项目 `GET /projects`、`GET /projects/{id}`（付费锁定）

### M2 · 投稿 + 大模型加工 + 审核 + 积分
- 投稿 `POST /submissions`、我的投稿 `GET /submissions/me`
  - 状态机：`draft → processing → pending_review → published / rejected`
  - LLM 抽象（`MockLLM` / `DoubaoClient`），无 key 回退 mock
- 积分 `GET /points/me`（余额 + 账本，发放以 `(ref_type, ref_id)` 幂等）
- 管理后台（需 `admin` 角色）
  - 审核队列 `GET /admin/submissions?status=`
  - 通过 / 驳回 `POST /admin/submissions/{id}/approve|reject`
  - 分类维护 `GET|POST /admin/categories`、`PATCH|DELETE /admin/categories/{id}`

### M3 · 支付骨架 + 付费解锁
- 解锁 `POST /payment/unlock`（`{content_type, content_id, method}`，method=cash|points）
  - 现金走 `PaymentProvider`（当前 `MockProvider`）→ 订单 paid → `entitlement(source=purchase)`
  - 积分校验余额 → 扣分（账本负值）→ `entitlement(source=points)`
  - 同一内容重复解锁幂等（返回 `already_unlocked`）
- 已解锁 `GET /payment/entitlements/me`
- 付费内容访问控制：`GET /projects/{id}`、`GET /knowledge/{id}` 依据 entitlement/作者/管理员返回 `locked`
- 双标价见 `docs/points-and-payment.md`；种子含付费项目与付费八股各 1 条
