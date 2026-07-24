#!/usr/bin/env bash
#
# 一键启动前后端（本地开发；SQLite，无需 Docker/Redis）
#
# 用法：
#   ./dev.sh           启动前后端，保留已有数据（种子幂等，不会重复灌）
#   ./dev.sh --fresh   先重置 SQLite 数据库再启动（清空并重新灌种子）
#   ./dev.sh --help    查看帮助
#
# 后端： http://localhost:8000  （API 文档 /docs）
# 前端： http://localhost:3000
# 管理员种子账号： admin@example.com / admin12345
#
# 按 Ctrl+C 一次即可同时停止前后端。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=3000
FRESH=0

for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
    -h|--help)
      awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *) echo "未知参数：$arg（可用：--fresh / --help）"; exit 1 ;;
  esac
done

log()  { printf "\033[36m[dev]\033[0m %s\n" "$*"; }
err()  { printf "\033[31m[dev]\033[0m %s\n" "$*" >&2; }

kill_port() {
  local port="$1" pids
  pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    log "释放端口 ${port} (kill $(echo ${pids} | tr '\n' ' '))"
    # shellcheck disable=SC2086
    kill -9 ${pids} 2>/dev/null || true
  fi
}

# ---- 前置检查 ----
if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  err "未找到后端虚拟环境：$BACKEND/.venv"
  err "请先执行： cd backend && python3 -m venv .venv && .venv/bin/pip install -e \".[dev]\""
  exit 1
fi

# ---- 环境变量 ----
# 若外部已设置 DATABASE_URL 则沿用（可指向 Postgres）；否则本地默认 SQLite
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./dev.db}"
# 本地演示默认同步加工投稿，无需 Redis / Worker
export TASK_QUEUE_ENABLED="${TASK_QUEUE_ENABLED:-false}"

# 前端指向本地后端
if [ ! -f "$FRONTEND/.env.local" ]; then
  echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:$BACKEND_PORT" > "$FRONTEND/.env.local"
  log "已创建 frontend/.env.local → http://localhost:$BACKEND_PORT"
fi

# ---- 释放旧进程 ----
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"
sleep 1

# ---- 数据库准备 ----
cd "$BACKEND"
if [ "$FRESH" = "1" ]; then
  if [[ "$DATABASE_URL" == sqlite* ]]; then
    log "重置数据库（--fresh）：删除 backend/dev.db"
    rm -f dev.db
  else
    err "--fresh 仅对 SQLite 生效，当前 DATABASE_URL 非 SQLite，跳过重置。"
  fi
fi
log "应用数据库迁移（alembic upgrade head）"
.venv/bin/alembic upgrade head
log "校正数据库自增序列（Postgres；SQLite 自动跳过）"
PYTHONPATH="$BACKEND" .venv/bin/python -m scripts.fix_sequences
log "灌入种子数据（幂等）"
PYTHONPATH="$BACKEND" .venv/bin/python -m scripts.seed
log "灌入 SQL 题库（幂等 upsert）"
PYTHONPATH="$BACKEND" .venv/bin/python -m scripts.seed_sql_bank

# ---- 前端依赖 ----
if [ ! -d "$FRONTEND/node_modules" ]; then
  log "安装前端依赖（npm install）"
  (cd "$FRONTEND" && npm install)
fi

# ---- 启动并托管进程 ----
PIDS=()
cleanup() {
  trap - EXIT INT TERM
  echo
  log "正在停止前后端…"
  for pid in "${PIDS[@]:-}"; do [ -n "$pid" ] && kill "$pid" 2>/dev/null || true; done
  kill_port "$BACKEND_PORT"
  kill_port "$FRONTEND_PORT"
  log "已停止。"
}
trap cleanup EXIT INT TERM

log "启动后端 → http://localhost:$BACKEND_PORT  (文档 /docs)"
( cd "$BACKEND" && exec .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT" ) &
PIDS+=($!)

log "启动前端 → http://localhost:$FRONTEND_PORT"
( cd "$FRONTEND" && exec npm run dev ) &
PIDS+=($!)

log "全部启动完成。管理员：admin@example.com / admin12345 。按 Ctrl+C 结束。"
wait
