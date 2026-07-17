from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category
from app.modules.interview.models import Company, InterviewPost
from app.modules.knowledge.models import KnowledgeItem
from app.modules.projects.models import Project, ProjectQA
from app.modules.sql_bank.models import SqlQuestion


async def test_category_tree(client: AsyncClient, db: AsyncSession) -> None:
    root = Category(section="knowledge", name="Hive", slug="hive", order=1)
    db.add(root)
    await db.flush()
    child = Category(section="knowledge", name="优化", slug="opt", order=1, parent_id=root.id)
    db.add(child)
    await db.commit()

    resp = await client.get("/categories", params={"section": "knowledge"})
    assert resp.status_code == 200, resp.text
    tree = resp.json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Hive"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["slug"] == "opt"


async def test_category_invalid_section(client: AsyncClient) -> None:
    resp = await client.get("/categories", params={"section": "nope"})
    assert resp.status_code == 400


async def test_knowledge_list_and_detail(client: AsyncClient, db: AsyncSession) -> None:
    item = KnowledgeItem(title="数据倾斜", content_md="# body", status="published")
    draft = KnowledgeItem(title="草稿", content_md="x", status="draft")
    db.add_all([item, draft])
    await db.commit()
    await db.refresh(item)

    resp = await client.get("/knowledge")
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()["items"]]
    assert "数据倾斜" in titles
    assert "草稿" not in titles  # 非 published 不展示

    resp = await client.get(f"/knowledge/{item.id}")
    assert resp.status_code == 200
    assert resp.json()["content_md"] == "# body"


async def test_knowledge_search(client: AsyncClient, db: AsyncSession) -> None:
    db.add_all(
        [
            KnowledgeItem(title="Hive 数据倾斜", content_md="skew body", status="published"),
            KnowledgeItem(
                title="Spark 宽窄依赖", content_md="讲到数据倾斜的处理", status="published"
            ),
            KnowledgeItem(title="Kafka 分区", content_md="无关内容", status="published"),
        ]
    )
    await db.commit()

    # 命中标题
    resp = await client.get("/knowledge", params={"q": "Hive"})
    assert resp.status_code == 200
    titles = [i["title"] for i in resp.json()["items"]]
    assert titles == ["Hive 数据倾斜"]

    # 命中标题或正文（两条都含“数据倾斜”）
    resp = await client.get("/knowledge", params={"q": "数据倾斜"})
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert titles == {"Hive 数据倾斜", "Spark 宽窄依赖"}

    # 无命中
    resp = await client.get("/knowledge", params={"q": "不存在的关键词"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_sql_tags_split(client: AsyncClient, db: AsyncSession) -> None:
    q = SqlQuestion(
        title="连续登录",
        prompt_md="p",
        answer_md="a",
        tags="窗口函数,分组",
        status="published",
    )
    db.add(q)
    await db.commit()

    resp = await client.get("/sql-questions")
    assert resp.status_code == 200
    assert resp.json()[0]["tags"] == ["窗口函数", "分组"]


async def test_interview_by_company(client: AsyncClient, db: AsyncSession) -> None:
    company = Company(name="字节跳动")
    db.add(company)
    await db.flush()
    db.add(
        InterviewPost(
            company_id=company.id,
            title="数据开发一面",
            interview_type="campus",
            content_md="面试内容",
            status="published",
        )
    )
    await db.commit()
    await db.refresh(company)

    resp = await client.get("/companies")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "字节跳动"

    resp = await client.get(f"/companies/{company.id}/interviews-by-type")
    assert resp.status_code == 200
    campus = next(g for g in resp.json() if g["interview_type"] == "campus")
    assert campus["posts"][0]["title"] == "数据开发一面"


async def test_project_paid_is_locked(client: AsyncClient, db: AsyncSession) -> None:
    free = Project(
        title="免费项目",
        description_md="desc",
        implementation_md="impl-free",
        access_type="free",
        status="published",
    )
    paid = Project(
        title="付费项目",
        description_md="desc",
        implementation_md="impl-paid",
        access_type="paid",
        price_cash=Decimal("199.00"),
        price_points=2000,
        status="published",
    )
    db.add_all([free, paid])
    await db.flush()
    db.add(ProjectQA(project_id=free.id, question_md="q", answer_md="a", order=1))
    await db.commit()
    await db.refresh(free)
    await db.refresh(paid)

    resp = await client.get(f"/projects/{free.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["locked"] is False
    assert body["implementation_md"] == "impl-free"
    assert len(body["qa"]) == 1

    resp = await client.get(f"/projects/{paid.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["locked"] is True
    assert body["implementation_md"] is None
    assert body["qa"] == []
