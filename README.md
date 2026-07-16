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

## 目录结构（规划）

```
de-platform/
  frontend/   # Next.js（后续里程碑落地）
  backend/    # FastAPI（后续里程碑落地）
  infra/      # docker-compose、部署脚本、CI（后续里程碑落地）
  docs/       # 规格 + 过程文档（当前阶段）
```

## 当前状态

📄 **文档先行阶段**：先沉淀规格与协作规范，代码工程骨架在 M0 里程碑落地。详见 [docs/roadmap.md](docs/roadmap.md)。

## 本地开发（待 M0 后补充）

初始化脚本、`docker-compose`、一键启动说明将在工程骨架落地后写入本节。
