"""Sổ đơn của Ban tổ chức (và toàn sàn khi organizer_id=None — dùng cho Admin)"""
import re
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, func, literal, literal_column, or_, select, true
from sqlalchemy.orm import Session

from app.services import sql_queries

from app.middlewares.errors import not_found
from app.models.catalog import Event, Show, TicketTier
from app.models.sales import Order, OrderItem, Ticket
from app.models.users import Organizer
from app.services.catalog import _escape_like
from app.services.manage import EVENT_NOT_FOUND
from app.utils.timefmt import VN, iso_vn
from app.utils.validators import as_str

ORDER_STATUSES = ("all", "paid", "refunded", "cancelled")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[0-9]{1,10}$")
MAX_Q = 100
MAX_PAGE_SIZE = 100


def own_event(db: Session, organizer_id: int, event_id: int) -> Event:
    """Sự kiện của chính Ban tổ chức; của người khác / không có → 404 (không lộ là có tồn tại)"""
    ev = db.scalar(select(Event).where(Event.id == event_id, Event.organizer_id == organizer_id))
    if ev is None:
        raise not_found(EVENT_NOT_FOUND)
    return ev


def parse_day(raw: str | None, field: str) -> date | None:
    """'YYYY-MM-DD' (ngày giờ VN) hoặc rỗng → None; sai → 400"""
    s = as_str(raw).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s) if DATE_RE.match(s) else _bad_day(field)
    except ValueError:
        return _bad_day(field)


def _bad_day(field: str):
    raise HTTPException(400, f"Ngày {field} không hợp lệ")


def _int_param(raw: Any, default: int, lo: int, hi: int, message: str) -> int:
    s = as_str(raw).strip()
    if not s:
        return default
    if not re.fullmatch(r"[0-9]{1,6}", s) or not lo <= int(s) <= hi:
        raise HTTPException(400, message)
    return int(s)


def parse_list_params(*, q: Any, event_id: Any, status: Any, day_from: Any, day_to: Any, page: Any,
                      page_size: Any) -> dict:
    """Kiểm tra tham số query của sổ đơn (dùng chung BTC và Admin)"""
    status = as_str(status).strip() or "all"
    if status not in ORDER_STATUSES:
        raise HTTPException(400, "Trạng thái đơn không hợp lệ")
    eid = as_str(event_id).strip()
    if eid and (not ID_RE.match(eid) or int(eid) > 2_147_483_647):
        raise HTTPException(400, "Mã sự kiện không hợp lệ")
    d0, d1 = parse_day(day_from, "from"), parse_day(day_to, "to")
    if d0 and d1 and d0 > d1:
        raise HTTPException(400, "Khoảng ngày không hợp lệ")
    return {
        "q": as_str(q).strip()[:MAX_Q], "event_id": int(eid) if eid else None, "status": status,
        "day_from": d0, "day_to": d1,
        "page": _int_param(page, 1, 1, 100_000, "Số trang không hợp lệ"),
        "page_size": _int_param(page_size, 20, 1, MAX_PAGE_SIZE, "Kích thước trang không hợp lệ"),
    }


def vn_start(day: date) -> datetime:
    """00:00 giờ VN của một ngày"""
    return datetime.combine(day, time(0, 0), tzinfo=VN)


def parse_organizer_id(raw: Any) -> int | None:
    """organizerId của bộ lọc Admin: rỗng → None; sai định dạng → 400"""
    s = as_str(raw).strip()
    if not s:
        return None
    if not ID_RE.match(s) or int(s) > 2_147_483_647:
        raise HTTPException(400, "Mã ban tổ chức không hợp lệ")
    return int(s)


SEARCH_EXPR = literal_column("lower(orders.id || ' ' || orders.buyer_name || ' ' || orders.buyer_email "
                             "|| ' ' || orders.buyer_phone)")


def _conditions(organizer_id: int | None, q: str, event_id: int | None, status: str,
                day_from: date | None, day_to: date | None) -> list:
    conds = []
    if organizer_id is not None:
        conds.append(Event.organizer_id == organizer_id)
    if event_id is not None:
        conds.append(Order.event_id == event_id)
    if status != "all":
        conds.append(Order.status == status)
    if day_from is not None:
        conds.append(Order.created_at >= vn_start(day_from))
    if day_to is not None:
        conds.append(Order.created_at < vn_start(day_to + timedelta(days=1)))
    if q:
        w = _escape_like(q)
        # (1) điều kiện CẦN trên biểu thức gộp có chỉ mục GIN trigram ix_orders_buyer_trgm (migration 0008) — planner
        #     dùng chỉ mục để thu hẹp; (2) điều kiện chính xác như cũ (mã đơn khớp TIỀN TỐ, các cột khác "chứa")
        conds.append(SEARCH_EXPR.like(func.lower(literal(f"%{w}%")), escape="\\"))
        conds.append(or_(Order.id.ilike(f"{w}%", escape="\\"), Order.buyer_name.ilike(f"%{w}%", escape="\\"),
                         Order.buyer_email.ilike(f"%{w}%", escape="\\"), Order.buyer_phone.ilike(f"%{w}%", escape="\\")))
    return conds


def _items_text(db: Session, order_ids: list[str]) -> dict[str, str]:
    """'Vé thường ×2, VIP ×1' theo thứ tự hạng vé (như manage._recent_orders)"""
    items: dict[str, list[str]] = {i: [] for i in order_ids}
    for it, name in db.execute(
        select(OrderItem, TicketTier.name)
        .join(TicketTier, (TicketTier.event_id == OrderItem.event_id) & (TicketTier.id == OrderItem.tier_id))
        .where(OrderItem.order_id.in_(order_ids)).order_by(TicketTier.sort_order, TicketTier.id)
    ):
        items[it.order_id].append(f"{name} ×{it.qty}")
    return {k: ", ".join(v) for k, v in items.items()}


def list_orders(db: Session, organizer_id: int | None, *, q: str, event_id: int | None, status: str,
                day_from: date | None, day_to: date | None, page: int, page_size: int,
                filter_organizer: int | None = None) -> dict:
    """Đơn mới trước; summary tính trên toàn bộ kết quả lọc (không chỉ trang hiện tại).
    organizer_id=None → toàn sàn (Admin), mỗi đơn kèm orgName (None = sàn tự bán); filter_organizer lọc theo một BTC.
    Truy vấn: backend/sql/queries/order_ledger.sql (Q1)."""
    platform = organizer_id is None
    w = _escape_like(q) if q else None
    rows = sql_queries.run(
        db, "order_ledger", org=organizer_id if not platform else filter_organizer, event=event_id, status=status,
        t0=vn_start(day_from) if day_from is not None else None,
        t1=vn_start(day_to + timedelta(days=1)) if day_to is not None else None,
        pat=f"%{w}%" if w else None, idpat=f"{w}%" if w else None,
        limit=page_size, offset=(page - 1) * page_size)
    head = rows[0]  # luôn có đúng một dòng tổng (LEFT JOIN trang) kể cả khi trang rỗng
    page_rows = [r for r in rows if r["id"] is not None]
    items = _items_text(db, [r["id"] for r in page_rows])
    return {
        "orders": [{
            "id": r["id"], "createdAt": iso_vn(r["created_at"]), "eventId": r["event_id"], "eventTitle": r["event_title"],
            "showId": r["show_id"], "startsAt": iso_vn(r["starts_at"]),
            "buyerName": r["buyer_name"], "buyerEmail": r["buyer_email"], "buyerPhone": r["buyer_phone"],
            "items": items.get(r["id"], ""), "tickets": int(r["tickets"]), "checkedIn": int(r["checked_in"]),
            "subtotal": r["subtotal"], "discount": r["discount"], "total": r["total"], "method": r["method"],
            "status": r["status"], "refundedAt": iso_vn(r["refunded_at"]),
            **({"orgName": r["org_name"]} if platform else {}),
        } for r in page_rows],
        "page": page, "pageSize": page_size, "total": int(head["total_count"]),
        "summary": {"paidOrders": int(head["paid_orders"]), "paidRevenue": int(head["paid_revenue"]),
                    "tickets": int(head["paid_tickets"])},
    }
