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

# 启动 API（http://localhost:8000，文档 /docs）
uvicorn app.main:app --reload
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

## 已实现（M0）

- 健康检查 `GET /health`
- 注册 `POST /auth/register`
- 登录 `POST /auth/login`（返回 access + refresh token）
- 刷新 `POST /auth/refresh`
- 当前用户 `GET /users/me`（需 Bearer token）
