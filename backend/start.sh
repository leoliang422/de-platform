#!/usr/bin/env bash
#
# 生产启动脚本（Render 等平台的 startCommand）。
# 先执行数据库迁移，可选灌种子，再以 $PORT 启动 uvicorn。
set -euo pipefail

echo "[start] 应用数据库迁移 alembic upgrade head"
alembic upgrade head

# 首次部署可设 SEED_ON_START=1 灌入初始种子（幂等：已有分类则跳过内容，仅确保管理员账号）
if [ "${SEED_ON_START:-0}" = "1" ]; then
  echo "[start] 灌入种子数据（幂等）"
  python -m scripts.seed || echo "[start] seed 跳过/失败（不阻塞启动）"
fi

echo "[start] 启动 uvicorn，端口 ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
