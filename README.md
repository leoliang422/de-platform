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

✅ **M0 · 工程脚手架 + 鉴权跑通**：后端注册/登录/JWT + 用户接口（含 pytest），前端首页/登录/注册 + 鉴权态，CI（后端 ruff+mypy+pytest，前端 eslint+tsc+build）。详见 [docs/roadmap.md](docs/roadmap.md)。

## 本地开发

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
