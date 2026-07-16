# de-platform · 数据开发学习 & 面试平台

面向数据开发（数仓 / 大数据方向）求职者的**学习 + 面试**一站式 Web 平台。

四大内容板块：
1. **八股总结** —— 按技术域（Hive / Spark / Flink / 数仓建模 …）分区，支持无限下钻的分类树。
2. **SQL 题库** —— 常见数据开发 SQL 题目与答案。
3. **面经** —— 按企业维度组织的面试经验。
4. **项目整理** —— 项目描述 / 实现 / 问答讲解，分免费与付费。

配套能力：用户体系、积分体系、支付（骨架）、大模型内容加工（投稿自动格式化 + 人工审核）。

> 本仓库同时作为**唯一事实来源**：规格文档、过程沉淀文档、以及项目本体全部在此维护。

## 文档索引（先看这里）

| 文档 | 说明 |
|---|---|
| [docs/spec.md](docs/spec.md) | 定稿规格说明书（需求、范围、验收标准） |
| [docs/architecture.md](docs/architecture.md) | 技术架构、模块划分、数据模型 |
| [docs/points-and-payment.md](docs/points-and-payment.md) | 积分规则与付费/解锁规则 |
| [docs/roadmap.md](docs/roadmap.md) | 里程碑与迭代计划 |
| [docs/collaboration.md](docs/collaboration.md) | 三人 vibe coding 协作规范 |
| [docs/api/README.md](docs/api/README.md) | 接口契约（OpenAPI）约定 |
| [docs/adr/](docs/adr/) | 架构决策记录（ADR） |
| [docs/process/](docs/process/) | 过程沉淀：会议纪要、复盘等 |

## 技术栈

- 前端：Next.js (React, App Router, TS) + Tailwind + shadcn/ui → Vercel
- 后端：FastAPI（模块化单体）→ Render / Railway
- 数据库：PostgreSQL（Neon）+ SQLAlchemy + Alembic
- 异步队列：ARQ + Redis（Upstash）
- 大模型：豆包（火山方舟 Ark，OpenAI 兼容），`LLMClient` 抽象，无 key 回退 `MockLLM`

## 目录结构

```
de-platform/
  frontend/   # Next.js (App Router, TS) + Tailwind
  backend/    # FastAPI（模块化单体）+ SQLAlchemy + Alembic
  infra/      # docker-compose、部署脚本
  docs/       # 规格 + 过程文档
```

## 当前状态

✅ 已完成 **M0–M3.1**：鉴权、四板块内容浏览、投稿+大模型加工(抽象)+审核、积分、支付骨架+付费解锁、管理员内容管理。
🚀 **M4 上线**：生产化改造 + 部署配置已就绪，按 [docs/deployment.md](docs/deployment.md)（Vercel + Render + Neon）即可上线。详见 [docs/roadmap.md](docs/roadmap.md)。

## 部署上线

一键化配置已备好（`render.yaml` / `backend/start.sh` / `frontend/vercel.json`）。完整点击流程见 **[docs/deployment.md](docs/deployment.md)**：Neon 建库 → Render 蓝图部署后端 → Vercel 部署前端 → 回填 CORS 联调。本次默认大模型/支付为 mock，投稿同步加工（无需 Redis）；真实能力均可只改环境变量切换。

## 本地开发

### 一键启动（推荐，SQLite，无需 Docker）

首次需先建后端虚拟环境与装依赖：

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && cd ..
```

之后在仓库根目录直接：

```bash
./dev.sh            # 启动前后端，保留已有数据
./dev.sh --fresh    # 重置数据库后启动（清空并重新灌种子）
```

- 后端 http://localhost:8000（文档 `/docs`）、前端 http://localhost:3000
- 管理员种子账号：`admin@example.com` / `admin12345`
- 脚本会自动释放 8000/3000 旧进程、跑迁移、灌幂等种子、按需装前端依赖；按一次 `Ctrl+C` 同时停止前后端。

### 手动方式（含 Docker + Postgres/Redis）

前置：Python 3.11+、Node 20+、Docker（本地 Postgres/Redis）。

```bash
# 1. 启动依赖服务
docker compose -f infra/docker-compose.yml up -d

# 2. 后端（http://localhost:8000，文档 /docs）
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# 3. 前端（http://localhost:3000）
cd ../frontend
npm install
npm run dev
```

各子项目详细说明见 [backend/README.md](backend/README.md)、[frontend/README.md](frontend/README.md)、[infra/README.md](infra/README.md)。
