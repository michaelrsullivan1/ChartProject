from fastapi import APIRouter

from app.api.routes.author_registry import router as author_registry_router
from app.api.routes.global_settings import router as global_settings_router
from app.api.routes.health import router as health_router
from app.api.routes.user_settings import router as user_settings_router
from app.api.routes.views import router as views_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(author_registry_router, tags=["author-registry"])
api_router.include_router(global_settings_router, tags=["global-settings"])
api_router.include_router(user_settings_router, tags=["user-settings"])
api_router.include_router(views_router, tags=["views"])
