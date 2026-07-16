from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.admin.content_router import router as admin_content_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.interview.router import router as interview_router
from app.modules.knowledge.router import router as knowledge_router
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
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(knowledge_router)
app.include_router(sql_router)
app.include_router(interview_router)
app.include_router(projects_router)
app.include_router(points_router)
app.include_router(submissions_router)
app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(admin_content_router)
