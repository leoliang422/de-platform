from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.modules.admin.content_router import router as admin_content_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.files.router import router as files_router
from app.modules.interactions.router import router as interactions_router
from app.modules.interview.router import router as interview_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.knowledge_tree.router import admin_router as knowledge_tree_admin_router
from app.modules.knowledge_tree.router import router as knowledge_tree_router
from app.modules.notifications.router import router as notifications_router
from app.modules.payment.router import router as payment_router
from app.modules.points.router import router as points_router
from app.modules.projects.router import router as projects_router
from app.modules.sql_bank.router import router as sql_router
from app.modules.submissions.router import router as submissions_router
from app.modules.users.router import router as users_router

settings = get_settings()

app = FastAPI(title="de-platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 本地存储：把上传目录挂到 /uploads 提供静态访问（S3 provider 时该目录可空置）。
_upload_dir = Path(settings.storage_local_dir)
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_upload_dir)), name="uploads")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(files_router)
app.include_router(catalog_router)
app.include_router(knowledge_router)
app.include_router(knowledge_tree_router)
app.include_router(knowledge_tree_admin_router)
app.include_router(sql_router)
app.include_router(interview_router)
app.include_router(projects_router)
app.include_router(points_router)
app.include_router(submissions_router)
app.include_router(notifications_router)
app.include_router(interactions_router)
app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(admin_content_router)
