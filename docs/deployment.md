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
| 真实支付 | `PAYMENT_PROVIDER=wechat` / `alipay` + 对应凭证 | 见下方「支付接入」；凭证未配齐时**自动回退 mock**，不影响现有功能 |

## 异步加工队列（M5-5B · Upstash Redis + Worker）

> 现状：投稿加工默认 **`TASK_QUEUE_ENABLED=false`（同步加工，无需 Redis）**，与之前一致。
> 代码已把「入队 → Worker 加工 → 落 `pending_review` / 失败落 `failed`」链路搭好，并做了
> **入队失败自动回退同步加工**，所以开启前后都不会让投稿卡死。

开启异步（可选，用于大模型加工较慢/量大时）：

1. **建 Redis**：打开 https://upstash.com → 建 Redis 数据库（选与 Render 就近区域），
   复制 **`rediss://...`** 连接串（TLS）。
2. **Render web 服务**：Environment 里设 `REDIS_URL=<上面的 rediss://...>`、`TASK_QUEUE_ENABLED=true`。
3. **启用 Worker 服务**：把 `render.yaml` 里被注释的 `de-platform-worker` 块取消注释，
   在 Render **Blueprint → Sync** 重新同步；给 worker 填 `DATABASE_URL`（同 Neon）与
   `REDIS_URL`（同上）。Worker 启动命令为 `arq app.workers.main.WorkerSettings`。
   - Worker 需常驻，建议 web + worker 都用 **Starter 档**（免费实例会休眠，不适合跑 worker）。
4. **验证**：投稿后接口立即返回 `status="processing"`；Worker 加工完成后变 `pending_review`。
   前端「我的投稿」轮询即可看到状态流转；失败会显示 `failed` 且可点重试
   （`POST /submissions/{id}/retry`，作者本人或管理员）。

> 本地联调：`export TASK_QUEUE_ENABLED=true REDIS_URL=redis://localhost:6379/0`，
> 另开一终端在 `backend/` 跑 `arq app.workers.main.WorkerSettings`。不设时保持同步加工。

## 文件存储（图片上传 · M6.2）

> 现状：默认 `STORAGE_PROVIDER=local`，图片存后端本地磁盘并由 `/uploads` 提供访问，
> **零外部依赖，本地/演示即可用**。抽象层已支持切换 S3 兼容对象存储，凭证未配齐时
> 自动回退 local，不影响现有功能。

⚠️ **Render 免费/Starter 的磁盘是临时的**，重启/重部署会丢失上传文件。**正式上线务必切对象存储**。

切换到 S3 兼容对象存储（推荐 Cloudflare R2，有免费额度；也可火山 TOS / AWS S3 / MinIO）：

1. 建 Bucket（设为可公开读，或挂 CDN 域名），拿到：`Endpoint`、`Region`、`Bucket`、
   `Access Key ID`、`Secret Access Key`、以及**公开访问域名**（`S3_PUBLIC_BASE_URL`）。
   - Cloudflare R2：控制台 → R2 → 建桶 → 「Manage R2 API Tokens」建密钥；开启「Public access」或绑自定义域。
2. Render 后端 Environment 填 `STORAGE_PROVIDER=s3` + 上述 `S3_*` 变量。
3. 代码里 `S3Storage.save()` 标了 `TODO(M6-real)`（用 boto3/aioboto3 `put_object`），补齐后即用。

## 支付接入（微信 / 支付宝）

> M5 现状：代码已把**支付抽象层、异步下单、回调结算（webhook）**都搭好，微信/支付宝
> 走「占位」模式——**默认 `PAYMENT_PROVIDER=mock`，同步结算**，与之前完全一致。当你把
> 下面的商户凭证配齐并切换 `PAYMENT_PROVIDER` 后即可启用真实支付；**任一凭证缺失都会
> 自动回退 mock**，所以随时可以先部署、后接入，不会影响已上线功能。
>
> 代码中 `create_charge` / `parse_callback` 的真实网关调用与验签处标了 `TODO(M5-real)`，
> 拿到凭证后按注释补齐即可（微信 v3 Native 下单 / 支付宝 page.pay）。

### 通用流程

1. 申请商户号、拿到下方凭证，填入 Render 后端 **Environment**。
2. 把 `PAYMENT_PROVIDER` 设为 `wechat` 或 `alipay`（一次只启用一个）。
3. 在支付平台后台配置**异步通知地址（回调 URL）**，指向后端：
   - 微信：`https://<你的后端域名>/payment/webhook/wechat`
   - 支付宝：`https://<你的后端域名>/payment/webhook/alipay`
4. 现金解锁时，后端返回 `status=pending` + `pay_url`（前端已适配跳转）；用户付款后
   支付平台回调上述 webhook，后端幂等结算订单并发放解锁权益。

### 微信支付（v3 · Native 扫码）凭证获取

| 变量 | 含义 | 从哪拿 |
|---|---|---|
| `WECHAT_APP_ID` | 公众号/小程序/开放平台 AppID | [微信公众平台](https://mp.weixin.qq.com) / 开放平台，需与商户号绑定 |
| `WECHAT_MCH_ID` | 商户号 | [微信支付商户平台](https://pay.weixin.qq.com) 完成商户入驻后获得 |
| `WECHAT_API_V3_KEY` | APIv3 密钥（回调解密/验签用） | 商户平台 → 账户中心 → API 安全 → 设置 APIv3 密钥（32 位，自己设定并保存） |
| `WECHAT_CERT_SERIAL` | 商户 API 证书序列号 | 商户平台 → API 安全 → 申请 API 证书后可见 |
| `WECHAT_PRIVATE_KEY_PATH` | 商户 API 私钥文件路径 | 申请 API 证书时下载的 `apiclient_key.pem`；部署到服务器路径填这里 |
| `WECHAT_NOTIFY_URL` | 异步通知地址 | 填 `https://<后端域名>/payment/webhook/wechat` |

> 前置资质：需**企业主体**开通微信支付商户号（个人主体一般无法开通 Native 支付）。

### 支付宝（电脑/手机网站支付）凭证获取

| 变量 | 含义 | 从哪拿 |
|---|---|---|
| `ALIPAY_APP_ID` | 应用 AppID | [支付宝开放平台](https://open.alipay.com) → 创建「网页/移动应用」后获得 |
| `ALIPAY_PRIVATE_KEY` | 应用私钥（RSA2） | 用支付宝「密钥生成工具」生成密钥对，私钥自留填这里 |
| `ALIPAY_PUBLIC_KEY` | 支付宝公钥 | 上传应用公钥后，平台生成的**支付宝公钥**（验签回调用），复制填这里 |
| `ALIPAY_GATEWAY` | 网关地址 | 生产 `https://openapi.alipay.com/gateway.do`（沙箱另有地址） |
| `ALIPAY_NOTIFY_URL` | 异步通知地址 | 填 `https://<后端域名>/payment/webhook/alipay` |

> 联调建议：先用支付宝**沙箱环境**（开放平台 → 研发服务 → 沙箱）拿沙箱 AppID/密钥/网关，
> 验证整条 `下单 → 付款 → 回调 → 解锁` 链路无误后，再切换到生产凭证。

### 安全提醒

- 私钥（`apiclient_key.pem` / `ALIPAY_PRIVATE_KEY`）与 `WECHAT_API_V3_KEY` 属高敏感信息，
  **只放 Render 环境变量，切勿提交进仓库**（`.env` 已被 gitignore）。
- webhook 无登录鉴权，安全性由**平台验签**保证——真实接入务必在 `parse_callback` 完成验签。

## 安全清单（上线务必确认）

- [ ] `APP_SECRET_KEY` 为随机强密钥（Render 已自动生成，勿用 `change-me`）
- [ ] `CORS_ORIGINS` 仅包含你的前端域名
- [ ] 首次部署后把 `SEED_ON_START` 改回 `0`，并修改/删除默认管理员口令
- [ ] Neon 连接串保密（勿提交进仓库）

## 常见问题

- **前端能打开但请求失败/CORS 报错**：确认 Render 的 `CORS_ORIGINS` 与前端域名完全一致（含 `https://`，无结尾斜杠），且 Vercel 的 `NEXT_PUBLIC_API_BASE_URL` 指向 Render。
- **后端启动失败**：查看 Render 日志，多为 `DATABASE_URL` 未填或 Neon 连接串错误。
- **首屏很慢**：Render 免费实例休眠冷启动，属正常；付费实例或定时保活可缓解。
