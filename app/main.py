from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routes import router
from app.config import get_settings


settings = get_settings()

app = FastAPI(
    title="QueueStorm Investigator",
    version=settings.app_version,
)

register_exception_handlers(app)
app.include_router(router)

