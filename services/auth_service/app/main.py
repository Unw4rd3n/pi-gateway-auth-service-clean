from fastapi import FastAPI

from .config import settings
from .db import Base, engine
from .routers import admin, auth


app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth"}


app.include_router(auth.router)
app.include_router(admin.router)
