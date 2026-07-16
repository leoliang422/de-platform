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
- [x] 分类树 `catalog`（无限下钻）
- [x] 四大板块只读展示：八股 / SQL / 面经（按企业）/ 项目
- [x] 种子数据脚本（示例内容）
- [x] 前端四大板块页面 + 分类导航

## M2 · 投稿 + 大模型加工 + 审核
- [x] `submissions` 投稿模型 + 状态机
- [x] `llm` 抽象 + `MockLLM` + 豆包实现
- [x] ARQ + Redis 异步加工任务 + Worker（本地默认同步加工）
- [x] 管理员后台 `/admin`：审核队列、分类维护（内容管理见 M3.1）
- [x] 前端投稿页 + 审核页 + 积分中心
- [x] `points` 账本 + 幂等发放（审核通过触发，M3 提前落地）

## M3 · 积分 + 支付骨架 + 付费解锁
- [x] `points` 账本 + 幂等发放（审核通过触发）— M2 已落地
- [x] `payment`：订单 + `MockProvider` + `entitlement`
- [x] 双标价与二选一解锁（现金 mock / 积分）
- [x] 付费内容访问控制（project / paid knowledge，作者/管理员/已解锁可见）
- [x] 前端：积分中心、购买/兑换、解锁态展示、已解锁列表

## M3.1 · 管理员内容管理（补齐 spec §8）
- [x] `/admin/content/{type}` 四类内容后台 CRUD（新建/编辑/删除）
- [x] 全状态列表（含 draft/rejected）+ 上下架（published ↔ draft）
- [x] 管理员直接粘贴 Markdown 录入（跳过大模型加工）
- [x] 前端 `/admin` 内容管理面板（tab + 列表 + 表单）
- [x] 前端 422 校验错误友好展示

## M4 · UI 打磨 + 部署演示
- [ ] UI/交互统一打磨（现代简洁风）
- [ ] 部署：前端 Vercel、后端/Worker Render/Railway、Neon、Upstash
- [ ] 端到端演示走查（对齐 spec 第 10 节验收标准）
- [ ] README 补充本地一键启动 + 部署说明
