from fastapi import APIRouter

from app.api.routes import drive, login, private, rename, service_accounts, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(service_accounts.router)
api_router.include_router(drive.router)
api_router.include_router(rename.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
