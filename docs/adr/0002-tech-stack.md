# ADR 0002: 技术栈与整体架构选型

- 状态：已接受
- 日期：2026-07-16

## 背景

需要一套适合三人快速 vibe coding、又能支撑后续扩展（内容动态扩展、支付通道接入、大模型加工）的技术栈。约束：前端偏好 React，后端偏好 Python，云托管优先，默认接豆包大模型。

## 决策

- 前端：Next.js (App Router, TS) + Tailwind + shadcn/ui，部署 Vercel。
- 后端：FastAPI **模块化单体**，分层 router→service→repository→model，部署 Render/Railway。
- 数据库：PostgreSQL（Neon）+ SQLAlchemy + Alembic。
- 异步队列：ARQ + Redis（Upstash），独立 Worker 跑大模型加工。
- 鉴权：邮箱+密码，JWT（access+refresh）+ bcrypt。
- 大模型：豆包（火山方舟 Ark，OpenAI 兼容），经 `LLMClient` 抽象，无 key 回退 `MockLLM`。
- 支付：`PaymentProvider` 抽象 + `MockProvider`，真实通道后置。
- 仓库：Monorepo 单仓。

## 备选与取舍

- 后端 Django：自带 admin 很香，但偏重、异步生态弱于 FastAPI，且我们要大量 LLM 异步调用，故选 FastAPI + 自建后台接口。
- 队列 Celery：生态大但偏重，ARQ 与 asyncio 更契合、更轻。
- Next.js 全栈：省一个服务，但用户明确要 Python 后端，故前后端分离。

## 后果

- 早期部署简单，后续可将 `modules/*` 平滑拆分为独立服务。
- 前端 Vercel、后端另托管，需维护两处部署与 CORS/环境变量约定。
