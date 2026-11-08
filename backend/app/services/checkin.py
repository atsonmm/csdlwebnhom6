"""Soát vé tại cổng (Ban tổ chức) và tra cứu mã vé chỉ xem (Admin, Task C3)"""
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.catalog import Event, MapSeat, Show, TicketTier
from app.models.sales import Order, Ticket
from app.models.users import Organizer
from app.services import manage
from app.utils.timefmt import VN, iso_vn

CODE_RE = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{4}$")
BAD_CODE = "Mã vé không hợp lệ"
TICKET_NOT_FOUND = "Không tìm thấy vé"
NOT_PAID = "Vé thuộc đơn đã hoàn tiền hoặc đã huỷ"


def normalize_code(raw: Any) -> str | None:
    """Bỏ khoảng trắng, viết hoa, "K7QF29XM" → "K7QF-29XM" (định dạng của booking.new_ticket_code); sai → None"""
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", "", raw).upper()
    if len(s) == 8 and "-" not in s:
        s = f"{s[:4]}-{s[4:]}"
    return s if CODE_RE.match(s) else None


def _find(db: Session, code: str, organizer_id: int | None):
    """Vé + đơn + sự kiện + suất + tên hạng + nhãn ghế (cùng chữ với vé của khách ở booking.orders_json)"""
    stmt = (select(Ticket, Order, Event, Show.starts_at, TicketTier.name, MapSeat.label)
            .join(Order, Order.id == Ticket.order_id)
            .join(Event, Event.id == Ticket.event_id)
            .join(Show, (Show.event_id == Order.event_id) & (Show.id == Order.show_id))
            .join(TicketTier, (TicketTier.event_id == Ticket.event_id) & (TicketTier.id == Ticket.tier_id))
            .outerjoin(MapSeat, (MapSeat.map_id == Event.map_id) & (MapSeat.id == Ticket.seat_id))
            .where(Ticket.code == code))
    if organizer_id is not None:
        stmt = stmt.where(Event.organizer_id == organizer_id)
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(404, TICKET_NOT_FOUND)
    return row


def _ticket_json(ticket: Ticket, order: Order, ev: Event, starts_at, tier_name: str, seat: str | None, checked_at) -> dict:
    return {"code": ticket.code, "orderId": order.id, "eventId": ev.id, "eventTitle": ev.title, "showId": order.show_id,
            "startsAt": iso_vn(starts_at), "tierName": tier_name, "seat": seat, "buyerName": order.buyer_name,
            "checkedInAt": iso_vn(checked_at)}


def check_in(db: Session, organizer_id: int, raw_code: Any) -> dict:
    code = normalize_code(raw_code)
    if code is None:
        raise HTTPException(400, BAD_CODE)
    ticket, order, ev, starts_at, tier_name, seat = _find(db, code, organizer_id)
    if order.status != "paid":
        raise HTTPException(409, NOT_PAID)
    # Ghi có điều kiện: hai cổng quét cùng mã → chỉ một lần nhận checked-in, lần sau thấy giờ soát đầu
    first = db.execute(update(Ticket).where(Ticket.code == code, Ticket.checked_in_at.is_(None))
                       .values(checked_in_at=func.now()).returning(Ticket.checked_in_at)).scalar()
    checked_at = first or db.scalar(select(Ticket.checked_in_at).where(Ticket.code == code))
    paid_in_show = (Order.event_id == order.event_id, Order.show_id == order.show_id, Order.status == "paid")
    total, done = db.execute(select(func.count(), func.count(Ticket.checked_in_at))
                             .select_from(Ticket).join(Order, Order.id == Ticket.order_id).where(*paid_in_show)).one()
    return {
        "result": "checked-in" if first else "already",
        "ticket": _ticket_json(ticket, order, ev, starts_at, tier_name, seat, checked_at),
        "showToday": starts_at.astimezone(VN).date() == manage.now_utc().astimezone(VN).date(),
        "progress": {"checkedIn": int(done), "total": int(total)},
    }


def lookup(db: Session, raw_code: Any) -> dict:
    """Admin tra cứu một mã vé bất kỳ trên sàn — chỉ đọc, KHÔNG đổi checked_in_at"""
    code = normalize_code(raw_code)
    if code is None:
        raise HTTPException(400, BAD_CODE)
    ticket, order, ev, starts_at, tier_name, seat = _find(db, code, None)
    org = db.get(Organizer, ev.organizer_id) if ev.organizer_id is not None else None
    return {
        "ticket": _ticket_json(ticket, order, ev, starts_at, tier_name, seat, ticket.checked_in_at),
        "order": {"id": order.id, "status": order.status, "total": order.total, "createdAt": iso_vn(order.created_at),
                  "buyerName": order.buyer_name, "buyerEmail": order.buyer_email},
        "event": {"id": ev.id, "title": ev.title, "slug": ev.slug, "status": ev.status,
                  "orgName": org.org_name if org else None},
    }
