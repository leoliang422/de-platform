# infra

本地基础设施与部署相关脚本。

## 本地依赖服务

启动 Postgres + Redis：

```bash
docker compose -f infra/docker-compose.yml up -d
```

- Postgres：`localhost:5432`，用户/密码/库 = `de` / `de` / `de_platform`
- Redis：`localhost:6379`

对应后端 `.env`：

```
DATABASE_URL=postgresql+asyncpg://de:de@localhost:5432/de_platform
REDIS_URL=redis://localhost:6379/0
```

停止：

```bash
docker compose -f infra/docker-compose.yml down
```

## 部署（后续 M4 补充）

- 前端：Vercel
- 后端 API / Worker：Render / Railway
- Postgres：Neon
- Redis：Upstash
