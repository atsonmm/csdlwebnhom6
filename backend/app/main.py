"""Ứng dụng FastAPI của TicketNhịp — mọi API nằm dưới /api"""
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.database import get_db
from app.middlewares.errors import install_error_handlers
from app.middlewares.request_guard import install_request_guard
from app.utils.spa import install_spa
from app.routers import admin, auth, catalog, manage, orders, organizer

app = FastAPI(title="TicketNhịp API")
install_error_handlers(app)

install_request_guard(app)

api = APIRouter(prefix="/api")


@api.get("/health", tags=["Hệ thống"])
def health(db: Session = Depends(get_db)) -> dict:
    version = db.execute(text("SHOW server_version")).scalar_one()
    return {"ok": True, "postgres": version}


app.include_router(api)
app.include_router(catalog.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(manage.router, prefix="/api")
app.include_router(organizer.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if settings.env == "prod" and (DIST / "index.html").is_file():
    install_spa(app, DIST)
