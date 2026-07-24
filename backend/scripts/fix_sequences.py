"""启动时校正 Postgres 各表自增主键序列，避免历史/导入数据导致的主键冲突（表现为插入报 500）。

背景：Postgres 用序列(sequence)给自增 id 赋值；若曾以显式 id 写入数据（导入/恢复/分支复制等），
序列可能落后于表内最大 id，下一次插入就会命中已存在的 id → 唯一键冲突 → 500。
本脚本把每张表的 id 序列对齐到 MAX(id)，幂等、安全，可在每次部署后运行。

SQLite 无序列机制，直接跳过（本地开发无需处理）。
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

import app.models  # noqa: F401  (确保所有表注册到 Base.metadata)
from app.core.database import Base, engine


async def fix_sequences() -> None:
    if not engine.url.get_backend_name().startswith("postgresql"):
        print("[fix_sequences] 非 Postgres，跳过序列校正。")
        return

    fixed = 0
    async with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            pk_cols = list(table.primary_key.columns)
            # 仅处理单列、名为 id 的自增主键
            if len(pk_cols) != 1 or pk_cols[0].name != "id":
                continue
            seq = (
                await conn.execute(
                    text("SELECT pg_get_serial_sequence(:tbl, 'id')"),
                    {"tbl": table.name},
                )
            ).scalar()
            if not seq:
                continue  # 该表 id 无关联序列（无需校正）
            # 表名来自 metadata（非用户输入），可安全拼接。
            max_id = (
                await conn.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table.name}"'))
            ).scalar() or 0
            # max_id>0：设为 max_id 且 is_called=true → 下一个为 max_id+1；
            # 空表：设为 1 且 is_called=false → 下一个为 1。
            await conn.execute(
                text("SELECT setval(:seq, :val, :called)"),
                {"seq": seq, "val": max(int(max_id), 1), "called": int(max_id) > 0},
            )
            fixed += 1
            print(f"[fix_sequences] 已校正 {table.name}.id 序列（max_id={max_id}）")
    print(f"[fix_sequences] 完成，共校正 {fixed} 张表。")


if __name__ == "__main__":
    asyncio.run(fix_sequences())
