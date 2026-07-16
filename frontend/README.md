# frontend · Next.js

数据开发学习 & 面试平台前端。Next.js (App Router) + TypeScript + Tailwind CSS。

## 环境要求

- Node.js 24（见 `.nvmrc`）
- 后端 API 运行中（默认 `http://localhost:8000`）

> 安装依赖统一用 `npm install`（不要用 `npm ci`）：`eslint-config-next` 传递依赖
> `unrs-resolver` 的平台原生绑定会被 npm 写成**无 version 的桩条目**，导致跨平台
> `npm ci` / `npm install` 报 `Invalid Version`。仓库里的 lockfile 已剥离这些桩条目。
>
> ⚠️ 若你在本机 `npm install` 后发现 `package-lock.json` 里又冒出无 version 的
> `@unrs/resolver-binding-*` 条目，请在提交前剥离它们（否则会再次弄挂 CI）：
>
> ```bash
> node -e "const fs=require('fs');const p='package-lock.json';const d=JSON.parse(fs.readFileSync(p));for(const k of Object.keys(d.packages))if(d.packages[k].version===undefined&&d.packages[k].optional)delete d.packages[k];fs.writeFileSync(p,JSON.stringify(d,null,2)+'\n')"
> ```

## 快速开始

```bash
cd frontend
npm install

# 配置后端地址（可选，默认 http://localhost:8000）
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

npm run dev   # http://localhost:3000
```

## 常用命令

```bash
npm run dev        # 开发
npm run build      # 生产构建
npm run lint       # ESLint
npm run typecheck  # 类型检查
```

## 已实现（M0）

- 首页：四大板块入口展示
- 注册 / 登录页，JWT 存 localStorage
- 顶部导航：登录态、昵称与积分展示

## 目录

```
app/            # 路由与页面（App Router）
  login/        # 登录
  register/     # 注册
components/     # 复用组件（Navbar）
lib/            # api 封装、鉴权 Context
```

> UI 组件库（shadcn/ui）将在后续里程碑按需引入；M0 使用原生 Tailwind。
