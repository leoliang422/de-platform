# 部署上线指南（Vercel + Render + Neon）

本项目 M4 的上线链路：**前端 Vercel · 后端 Render · 数据库 Neon Postgres**（均有免费额度）。
大模型本次保持 `mock`，支付保持 `mock`，投稿同步加工（无需 Redis）。

架构：

```
浏览器 ──> Vercel (Next.js 前端, NEXT_PUBLIC_API_BASE_URL)
                     │  https
                     ▼
              Render (FastAPI 后端)  ──asyncpg/SSL──>  Neon (Postgres)
```

> 前置：代码已在 GitHub（`main` 分支）。以下三个平台都用 GitHub 账号登录、授权本仓库即可。

---

## 1. Neon：创建 Postgres 数据库

1. 打开 https://neon.tech → 用 GitHub 登录 → **Create project**。
2. 选区域（建议 `AWS ap-southeast-1 / Singapore`，与 Render 就近）。
3. 创建后在 **Connection Details** 复制连接串，形如：
   ```
   postgresql://<user>:<password>@ep-xxx-xxx.ap-southeast-1.aws.neon.tech/<db>?sslmode=require
   ```
   记为 `DATABASE_URL`（后端代码会自动转成 asyncpg + SSL，无需改写）。

## 2. Render：部署后端（FastAPI）

用仓库根目录的 `render.yaml`（蓝图）一键创建：

1. 打开 https://render.com → GitHub 登录。
2. **New +** → **Blueprint** → 选择本仓库 → Render 读取 `render.yaml` 生成服务 `de-platform-api`。
3. 部署前/后在服务 **Environment** 里补两个未同步的变量：
   - `DATABASE_URL` = 第 1 步的 Neon 连接串
   - `CORS_ORIGINS` = 你的前端域名（第 3 步拿到后回填，可先留 `https://<项目名>.vercel.app`）
   - （`APP_SECRET_KEY` 已配置为自动生成；`SEED_ON_START=1` 会在首次启动灌入种子含管理员账号）
4. 部署完成后拿到后端地址，形如 `https://de-platform-api.onrender.com`。
   - 健康检查：访问 `/health` 应返回 `{"status":"ok"}`
   - API 文档：`/docs`

> 说明：`start.sh` 会先 `alembic upgrade head` 建表，再启动。Render 免费实例会休眠，首次冷启动稍慢属正常。

## 3. Vercel：部署前端（Next.js）

1. 打开 https://vercel.com → GitHub 登录 → **Add New… → Project** → 选本仓库。
2. **Root Directory** 选 `frontend`（关键：这是 monorepo）。框架会自动识别 Next.js。
3. **Environment Variables** 添加：
   - `NEXT_PUBLIC_API_BASE_URL` = 第 2 步的 Render 后端地址（例：`https://de-platform-api.onrender.com`）
4. Deploy，完成后拿到前端地址，例如 `https://de-platform.vercel.app`。

## 4. 回填 CORS 并联调

1. 回到 Render，把 `CORS_ORIGINS` 改成真实前端域名（多个用逗号分隔），保存触发重启。
2. 打开前端域名，走一遍：注册 → 登录 → 浏览四板块 → 投稿 → 管理员 `/admin` 审核/内容管理 → 积分/解锁。
   - 管理员默认：`admin@example.com` / `admin12345`（**上线后请立刻改密码或重建管理员**）。

---

## 上线后可选：切换到"真实"能力（都只改环境变量，不改代码）

| 能力 | 变量 | 说明 |
|---|---|---|
| 真实豆包大模型 | `LLM_PROVIDER=doubao` + `DOUBAO_API_KEY=<key>` | 火山方舟 Ark，OpenAI 兼容；无 key 自动回退 mock |
| 异步加工队列 | `TASK_QUEUE_ENABLED=true` + `REDIS_URL=<Upstash>` | 需另起 Worker：`arq app.workers.main.WorkerSettings` |
| 真实支付 | `PAYMENT_PROVIDER=wechat/alipay/stripe` | 需实现对应 Provider + 商户资质（尚未接入） |

## 安全清单（上线务必确认）

- [ ] `APP_SECRET_KEY` 为随机强密钥（Render 已自动生成，勿用 `change-me`）
- [ ] `CORS_ORIGINS` 仅包含你的前端域名
- [ ] 首次部署后把 `SEED_ON_START` 改回 `0`，并修改/删除默认管理员口令
- [ ] Neon 连接串保密（勿提交进仓库）

## 常见问题

- **前端能打开但请求失败/CORS 报错**：确认 Render 的 `CORS_ORIGINS` 与前端域名完全一致（含 `https://`，无结尾斜杠），且 Vercel 的 `NEXT_PUBLIC_API_BASE_URL` 指向 Render。
- **后端启动失败**：查看 Render 日志，多为 `DATABASE_URL` 未填或 Neon 连接串错误。
- **首屏很慢**：Render 免费实例休眠冷启动，属正常；付费实例或定时保活可缓解。
