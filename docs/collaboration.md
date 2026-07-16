# 三人 vibe coding 协作规范

全员协同、不固定分工，任何人都能拎起任何模块。核心：**小 PR、强边界、契约先行、绿灯合并**，降低 AI 生成代码互相冲突的概率。

## 1. 仓库模式

- **Monorepo 单仓**：`frontend/` + `backend/` + `infra/` + `docs/` 同仓，联调最省事。
- GitHub 上以 Issue + Projects 看板管理任务；谁空谁认领。

## 2. 分支策略

- `main`：受保护主干，**禁止直接 push**，只能经 PR 合入。
- 功能分支：`feat/*`、`fix/*`、`docs/*`、`chore/*`。
- 合并：**Squash merge**，保持主干线性整洁。

## 3. PR 流程

1. 从最新 `main` 切分支。
2. **小而聚焦**：一次一个功能点，尽量 < 400 行 diff。
3. 填 PR 模板、关联 Issue。
4. CI 全绿 + **至少 1 人 review** → 合并。
5. 合并后删除功能分支。

## 4. 降冲突约定（vibe coding 关键）

- 按 `backend/app/modules/*` 领域边界改动；跨模块只经 service 接口，不碰对方 repository/model。
- 动手前先在看板认领任务，避免两人同时改同一模块。
- 影响架构 / 接口 / 数据模型的改动，先写一条 [ADR](adr/) 再动手。
- 接口先在 [api](api/) 约定，前后端各自并行（后端出 `/docs`，前端用 mock）。

## 5. 代码规范与 CI

- 后端：`ruff`（lint+format）+ `mypy`（类型）+ `pytest`（测试）。
- 前端：`eslint` + `tsc` + `next build`。
- CI 未通过不允许合并。

## 6. 提交信息

Conventional Commits：`feat: ...` / `fix: ...` / `docs: ...` / `refactor: ...` / `chore: ...`。

## 7. 密钥管理

- 配置全部走环境变量，模板见根目录 `.env.example`。
- 真实 `.env`、豆包 key、DB 密码等**各自本地保存，严禁提交**。

## 8. 文档沉淀

- 规格 / 架构 / 规则：`docs/*.md`，随功能演进同步更新（视为 PR 的一部分）。
- 决策：`docs/adr/`。
- 过程（会议纪要、复盘、排障记录）：`docs/process/`。
