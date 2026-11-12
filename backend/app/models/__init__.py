"""Đăng ký mọi model vào Base.metadata (Alembic và create_all cần import đủ)"""
from app.config.database import Base
from app.models import catalog, locations, payouts, questions, resale, sales, users  # noqa: F401
from app.models.comments import TABLE_COMMENTS

# Gắn chú thích bảng vào metadata để autogenerate không đòi xoá COMMENT của migration 0002
for _name, _comment in TABLE_COMMENTS.items():
    Base.metadata.tables[_name].comment = _comment
