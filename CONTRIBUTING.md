# 贡献与协作指南

三人协同、全员 vibe coding。核心原则：**小 PR、强边界、契约先行、绿灯合并**。完整规范见 [docs/collaboration.md](docs/collaboration.md)，这里是速查。

## 分支与提交

- `main` 为受保护主干，**禁止直接 push**。
- 功能分支命名：`feat/<简述>`、`fix/<简述>`、`docs/<简述>`、`chore/<简述>`。
- 提交信息用 [Conventional Commits](https://www.conventionalcommits.org/)：
  - `feat: 增加积分账本发放接口`
  - `fix: 修复投稿状态机重复发分`
  - `docs: 补充架构文档`

## Pull Request

1. 从最新 `main` 切出功能分支。
2. 保持 PR 小而聚焦（一次一个功能点，尽量 < 400 行 diff）。
3. 填写 PR 模板，关联 Issue。
4. CI 全绿 + 至少 1 人 review 通过后方可合并。
5. 合并方式：Squash merge，保持主干历史整洁。

## 减少 vibe coding 冲突

- 按 `backend/app/modules/*` 领域边界改动，跨模块只经 service 接口调用。
- 动手前先在 Issue / 看板认领任务，避免两人改同一模块。
- 大改动先在 `docs/adr/` 写一条决策记录（ADR）再动手。

## 密钥与配置

- 所有配置走环境变量，模板见 [.env.example](.env.example)。
- **严禁提交真实 `.env` 或任何密钥**（豆包 key、DB 密码等各自本地保存）。
