"""Seed sample content for local development / demo.

Run after applying migrations:

    cd backend
    alembic upgrade head
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401  (register models)
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.catalog.models import Category
from app.modules.interview.models import Company, InterviewPost
from app.modules.knowledge.models import KnowledgeItem
from app.modules.projects.models import Project, ProjectQA
from app.modules.sql_bank.models import SqlQuestion
from app.modules.users.models import User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin12345"


async def _ensure_admin(db: AsyncSession) -> None:
    existing = await db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    if existing is None:
        db.add(
            User(
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                nickname="管理员",
                role="admin",
            )
        )
        await db.commit()
        print(f"已创建管理员账号：{ADMIN_EMAIL} / {ADMIN_PASSWORD}")


async def seed() -> None:
    async with SessionLocal() as db:
        await _ensure_admin(db)

        existing = await db.scalar(select(func.count()).select_from(Category))
        if existing:
            print(f"已存在 {existing} 个分类，跳过内容种子灌入。")
            return

        # --- 分类树（八股） ---
        hive = Category(section="knowledge", name="Hive", slug="hive", order=1)
        spark = Category(section="knowledge", name="Spark", slug="spark", order=2)
        db.add_all([hive, spark])
        await db.flush()

        hive_opt = Category(
            section="knowledge",
            name="Hive 优化",
            slug="hive-optimize",
            order=1,
            parent_id=hive.id,
        )
        spark_core = Category(
            section="knowledge",
            name="Spark Core",
            slug="spark-core",
            order=1,
            parent_id=spark.id,
        )
        db.add_all([hive_opt, spark_core])
        await db.flush()

        db.add_all(
            [
                KnowledgeItem(
                    category_id=hive_opt.id,
                    title="Hive 数据倾斜的成因与解决方案",
                    content_md=(
                        "## 数据倾斜\n\n数据倾斜通常由 key 分布不均导致。常见解法：\n\n"
                        "- 开启 `hive.groupby.skewindata`\n- 加盐打散热点 key\n- Map Join 小表\n"
                    ),
                ),
                KnowledgeItem(
                    category_id=spark_core.id,
                    title="Spark 宽依赖与窄依赖",
                    content_md=(
                        "## 依赖关系\n\n- 窄依赖：父 RDD 分区一对一映射子分区\n"
                        "- 宽依赖：涉及 shuffle，是 Stage 划分边界\n"
                    ),
                ),
                KnowledgeItem(
                    category_id=spark_core.id,
                    title="Spark 调优体系（付费）",
                    content_md=(
                        "## 调优全景\n\n资源、并行度、shuffle、数据倾斜、AQE 全链路调优清单……\n"
                    ),
                    is_paid=True,
                    price_cash=Decimal("9.90"),
                    price_points=200,
                ),
            ]
        )

        # --- SQL 题库 ---
        sql_cat = Category(section="sql", name="窗口函数", slug="window-func", order=1)
        db.add(sql_cat)
        await db.flush()
        db.add(
            SqlQuestion(
                category_id=sql_cat.id,
                title="连续登录 3 天及以上的用户",
                difficulty="medium",
                prompt_md="给定登录表 `login(uid, dt)`，求连续登录 >= 3 天的用户。",
                answer_md=(
                    "```sql\nSELECT uid FROM (\n"
                    "  SELECT uid, dt,\n"
                    "    date_sub(dt, row_number() OVER (PARTITION BY uid ORDER BY dt)) AS grp\n"
                    "  FROM login\n) t\nGROUP BY uid, grp\nHAVING count(*) >= 3;\n```\n"
                ),
                tags="窗口函数,连续区间,分组",
            )
        )

        # --- 面经 ---
        company = Company(name="字节跳动")
        db.add(company)
        await db.flush()
        db.add(
            InterviewPost(
                company_id=company.id,
                position="数据开发工程师",
                content_md=(
                    "## 一面\n\n1. Hive 数据倾斜怎么处理？\n2. 手写连续登录 SQL\n3. "
                    "介绍一个你做过的数仓分层设计\n"
                ),
            )
        )

        # --- 项目（一个免费，一个付费）---
        free_project = Project(
            title="用户行为数仓分层建模（免费）",
            description_md="基于埋点日志，构建 ODS/DWD/DWS/ADS 分层数仓。",
            implementation_md="## 实现\n\n分层设计、维度建模、调度编排的完整实现说明……",
            level="basic",
            access_type="free",
        )
        paid_project = Project(
            title="实时数仓 Flink + CK 实战（付费）",
            description_md="端到端实时数仓：Flink 计算 + ClickHouse 存储 + 实时看板。",
            implementation_md="## 实现\n\n（付费内容，解锁后可见）",
            level="advanced",
            access_type="paid",
            price_cash=Decimal("199.00"),
            price_points=2000,
        )
        db.add_all([free_project, paid_project])
        await db.flush()
        db.add(
            ProjectQA(
                project_id=free_project.id,
                question_md="为什么要做数仓分层？",
                answer_md="解耦、复用、隔离原始数据与应用，提升可维护性与一致性。",
                order=1,
            )
        )

        await db.commit()
        print("种子数据灌入完成。")


if __name__ == "__main__":
    asyncio.run(seed())
