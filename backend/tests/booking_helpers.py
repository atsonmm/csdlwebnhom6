"""Tiện ích cho test đặt vé (CSDL test đã nạp catalog bằng fixture api/api_db)"""
import itertools
import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.catalog import Event, TicketTier
from app.models.sales import Order, OrderItem, SeatHold, Ticket, TierStock
from app.models.users import User
from app.utils.security import hash_password

LEGACY = json.loads((Path(__file__).resolve().parent / "fixtures/legacy_events.json").read_text(encoding="utf-8"))
PASSWORD = "matkhau1"
_PW_HASH = hash_password(PASSWORD)
_seq = itertools.count(1)


def make_customer(db: Session, email: str) -> User:
    u = User(name="Khách thử", email=email, password_hash=_PW_HASH)
    db.add(u)
    db.commit()
    return u


def login(client: TestClient, email: str, password: str = PASSWORD) -> None:
    r = client.post("/api/auth/login", json={"identifier": email, "password": password})
    assert r.status_code == 200, r.text


def event_id(db: Session, slug: str) -> int:
    return db.scalar(select(Event.id).where(Event.slug == slug))


def insert_order(db: Session, user: User, slug: str, show_id: str, items: list[tuple[str, int]] = (),
                 seats: list[tuple[str, str]] = (), created_at: datetime | None = None) -> Order:
    """Chèn đơn thẳng bằng ORM (để test phần ĐỌC đơn). seats: [(tier_id, seat_id)].
    Như đặt vé thật: trừ kho tier_stock của suất (nếu có dòng kho) — số "đã bán" đi qua stock.tier_stats."""
    eid = event_id(db, slug)
    n = next(_seq)
    lines: dict[str, int] = {}
    for tier_id, qty in items:
        lines[tier_id] = lines.get(tier_id, 0) + qty
    for tier_id, _seat in seats:
        lines[tier_id] = lines.get(tier_id, 0) + 1
    prices = {t: db.get(TicketTier, (eid, t)).price for t in lines}
    subtotal = sum(prices[t] * q for t, q in lines.items())
    o = Order(id=f"TNTEST{n:04d}", user_id=user.id, event_id=eid, show_id=show_id, subtotal=subtotal, discount=0,
              total=subtotal, method="qr", buyer_name="Người nhận", buyer_email="nhan@x.vn", buyer_phone="0912345678")
    if created_at is not None:
        o.created_at = created_at
    db.add(o)
    db.flush()
    db.add_all([OrderItem(order_id=o.id, event_id=eid, tier_id=t, price=prices[t], qty=q) for t, q in lines.items()])
    for tier_id, qty in items:
        db.execute(update(TierStock).where(TierStock.event_id == eid, TierStock.show_id == show_id,
                                           TierStock.tier_id == tier_id).values(sold=TierStock.sold + qty))
    k = 0
    for tier_id, qty in items:
        for _ in range(qty):
            k += 1
            db.add(Ticket(code=f"T{n:03d}-{k:04d}", order_id=o.id, event_id=eid, tier_id=tier_id, price=prices[tier_id]))
    for tier_id, seat_id in seats:
        k += 1
        db.add(SeatHold(event_id=eid, show_id=show_id, seat_id=seat_id, order_id=o.id))
        db.add(Ticket(code=f"T{n:03d}-{k:04d}", order_id=o.id, event_id=eid, tier_id=tier_id, price=prices[tier_id],
                      seat_id=seat_id))
    db.commit()
    return o
