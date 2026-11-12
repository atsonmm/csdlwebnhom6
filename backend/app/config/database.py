"""Kết nối PostgreSQL qua SQLAlchemy (đồng bộ)"""
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    # echo=True khi phát triển: in câu SQL thật ra log để trình bày
    # connect_timeout: PostgreSQL chưa bật thì báo lỗi sau vài giây thay vì treo mãi
    return create_engine(url, echo=settings.env == "dev", pool_pre_ping=True, connect_args={"connect_timeout": 3})


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
