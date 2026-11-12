"""Nạp và chạy các truy vấn nghiệp vụ viết bằng SQL thuần trong backend/sql/queries/*.sql (Task G3).

Mỗi file một truy vấn, đầu file là chú thích (mục đích – đầu vào – API dùng – người phụ trách). Tham số luôn là
bind parameter `:ten` (truyền qua text() của SQLAlchemy → psycopg gửi riêng giá trị) — KHÔNG ghép chuỗi giá trị
người dùng vào câu SQL.
"""
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

QUERIES_DIR = Path(__file__).resolve().parent.parent.parent / "sql" / "queries"
NAMES = ("order_ledger", "revenue_series", "revenue_running", "event_ranking", "tier_sell_through",
         "top_customers", "events_without_sales", "withdrawal_balance")


@lru_cache(maxsize=None)
def load(name: str) -> str:
    """Nội dung SQL (bỏ các dòng chú thích '--' để dấu ':' trong chú thích không bị hiểu là tham số)"""
    if name not in NAMES:
        raise KeyError(name)
    body = (QUERIES_DIR / f"{name}.sql").read_text(encoding="utf-8")
    return "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("--")).strip().rstrip(";")


# Truy vấn có bộ lọc tuỳ chọn dạng (:x IS NULL OR cột = :x): sau 5 lần chạy, psycopg tự prepare và PostgreSQL có thể
# chuyển sang generic plan (không biết :x có NULL hay không → bỏ chỉ mục, quét tuần tự). Ép custom plan cho riêng
# transaction đang chạy (SET LOCAL — commit / rollback là trả lại mặc định).
CUSTOM_PLAN = frozenset({"order_ledger"})


def run(db: Session, name: str, **params: Any) -> list[RowMapping]:
    if name in CUSTOM_PLAN:
        db.execute(text("SET LOCAL plan_cache_mode = force_custom_plan"))
    return list(db.execute(text(load(name)), params).mappings().all())
