# 里程碑与迭代计划

> 状态：v1.0 · 随进度通过 PR 勾选与更新

原则：里程碑之间尽量解耦，便于三人并行；契约先行，前后端不互相阻塞。

## M0 · 工程脚手架 + 鉴权跑通
- [ ] Monorepo 骨架：`frontend/` `backend/` `infra/`
- [ ] `infra/docker-compose.yml`（Postgres + Redis）
- [ ] GitHub Actions CI（后端 ruff+mypy+pytest，前端 eslint+tsc+build）
- [ ] 后端 FastAPI 基座 + `core`（配置/DB/Redis/异常/日志）
- [ ] 鉴权：注册 / 登录 / JWT / 角色，用户表 + 迁移
- [ ] 前端基座 + 登录注册页 + 鉴权态管理
- [ ] 主干保护与 PR 流程生效

## M1 · 内容浏览（只读）+ 种子数据
- [ ] 分类树 `catalog`（无限下钻）
- [ ] 四大板块只读展示：八股 / SQL / 面经（按企业）/ 项目
- [ ] 种子数据脚本（示例内容）
- [ ] 前端四大板块页面 + 分类导航

## M2 · 投稿 + 大模型加工 + 审核
- [ ] `submissions` 投稿模型 + 状态机
- [ ] `llm` 抽象 + `MockLLM` + 豆包实现
- [ ] ARQ + Redis 异步加工任务 + Worker
- [ ] 管理员后台 `/admin`：审核队列、内容 CRUD、分类维护
- [ ] 前端投稿页 + 审核页

## M3 · 积分 + 支付骨架 + 付费解锁
- [ ] `points` 账本 + 幂等发放（审核通过触发）
- [ ] `payment`：订单 + `MockProvider` + `entitlement`
- [ ] 双标价与二选一解锁（现金 mock / 积分）
- [ ] 付费内容访问控制
- [ ] 前端：积分中心、购买/兑换、解锁态展示

## M4 · UI 打磨 + 部署演示
- [ ] UI/交互统一打磨（现代简洁风）
- [ ] 部署：前端 Vercel、后端/Worker Render/Railway、Neon、Upstash
- [ ] 端到端演示走查（对齐 spec 第 10 节验收标准）
- [ ] README 补充本地一键启动 + 部署说明
