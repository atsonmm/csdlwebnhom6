"""Tiện ích cho test chợ vé bán lại (CSDL đã nạp catalog qua fixture api / api_db)"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Event, MapSeat, Show
from app.models.sales import SeatHold, Ticket
from tests.booking_helpers import event_id, insert_order

LIST_EVENT = "kich-hen-anh-o-ben-song"  # bán theo loại vé, 2 suất sắp diễn (vip / thuong)
SEAT_EVENT = "kich-tam-cam-dai-chien"  # bán theo ghế (vip / thuong)
BUYER = {"name": "Người Mua Lại", "email": "mualai@x.vn", "phone": "0912345678"}


def future_show(db: Session, slug: str, nth: int = 0) -> str:
    now = datetime.now(timezone.utc)
    ids = db.scalars(select(Show.id).where(Show.event_id == event_id(db, slug), Show.starts_at > now, Show.active)
                     .order_by(Show.starts_at, Show.id)).all()
    return ids[nth]


def buy(db: Session, user, slug: str = LIST_EVENT, tier: str = "thuong", n: int = 2, show: str | None = None):
    """Đơn đã thanh toán của user → (order, [mã vé])"""
    sid = show or future_show(db, slug)
    o = insert_order(db, user, slug, sid, items=[(tier, n)])
    return o, list(db.scalars(select(Ticket.code).where(Ticket.order_id == o.id).order_by(Ticket.code)))


def buy_seats(db: Session, user, slug: str = SEAT_EVENT, tier: str = "thuong", n: int = 2):
    """Đơn theo ghế (ghế còn trống của hạng) → (order, [mã vé], [mã ghế])"""
    sid = future_show(db, slug)
    ev = db.get(Event, event_id(db, slug))
    held = select(SeatHold.seat_id).where(SeatHold.event_id == ev.id, SeatHold.show_id == sid)
    seats = db.scalars(select(MapSeat.id).where(MapSeat.map_id == ev.map_id, MapSeat.group_id == tier,
                                                MapSeat.id.not_in(held)).order_by(MapSeat.sort_order).limit(n)).all()
    o = insert_order(db, user, slug, sid, seats=[(tier, s) for s in seats])
    codes = list(db.scalars(select(Ticket.code).where(Ticket.order_id == o.id).order_by(Ticket.code)))
    return o, codes, list(seats)


def face_price(db: Session, code: str) -> int:
    return db.get(Ticket, code).price
