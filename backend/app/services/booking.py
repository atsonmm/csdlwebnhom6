"""Đặt vé: mã đơn / mã vé, JSON đơn hàng (giống toOrderJson của bản Node), tạo đơn chống bán trùng."""
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.catalog import Event, MapSeat, Show, TicketTier
from app.models.sales import Coupon, Order, OrderItem, SeatHold, Ticket, TierStock
from app.models.users import User
from app.schemas.booking import OrderIn  # noqa: F401  (body request, dùng lại tên booking.OrderIn)
from app.config.rules import MAX_PER_ORDER
from app.services.catalog import public_events_query
from app.utils.timefmt import hhmm, iso_vn
from app.utils.validators import as_str, is_email, is_phone, normalize_phone

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bỏ I, O, 0, 1 cho dễ đọc
PAYMENT_METHODS = ("qr", "wallet", "card")


# ---------------------------------------------------------------- mã đơn / mã vé
def random_code(n: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def new_order_id(db: Session) -> str:
    while True:
        oid = "TN" + random_code(8)
        if db.get(Order, oid) is None:
            return oid


def new_ticket_code(db: Session) -> str:
    """Mã check-in dạng "K7QF-29XM": mỗi vé một mã, không trùng"""
    while True:
        c = random_code(8)
        code = f"{c[:4]}-{c[4:]}"
        if db.get(Ticket, code) is None:
            return code


# ---------------------------------------------------------------- đơn hàng → JSON
def orders_json(db: Session, orders: list[Order]) -> list[dict]:
    """JSON cho nhiều đơn bằng 4 truy vấn (sự kiện, suất, dòng đơn, vé)"""
    if not orders:
        return []
    ids = [o.id for o in orders]
    events = {e.id: e for e in db.scalars(select(Event).where(Event.id.in_({o.event_id for o in orders})))}
    shows = {(s.event_id, s.id): s for s in db.scalars(
        select(Show).where(tuple_(Show.event_id, Show.id).in_({(o.event_id, o.show_id) for o in orders})))}

    items: dict[str, list[dict]] = {i: [] for i in ids}
    for it, name in db.execute(
        select(OrderItem, TicketTier.name)
        .join(TicketTier, (TicketTier.event_id == OrderItem.event_id) & (TicketTier.id == OrderItem.tier_id))
        .where(OrderItem.order_id.in_(ids))
        .order_by(TicketTier.sort_order, TicketTier.id)
    ):
        items[it.order_id].append({"tierId": it.tier_id, "name": name, "price": it.price, "qty": it.qty})

    tickets: dict[str, list[dict]] = {i: [] for i in ids}
    for t, name, seat_label in db.execute(
        select(Ticket, TicketTier.name, MapSeat.label)
        .join(TicketTier, (TicketTier.event_id == Ticket.event_id) & (TicketTier.id == Ticket.tier_id))
        .join(Event, Event.id == Ticket.event_id)
        .outerjoin(MapSeat, (MapSeat.map_id == Event.map_id) & (MapSeat.id == Ticket.seat_id))
        .where(Ticket.order_id.in_(ids))
        .order_by(TicketTier.sort_order, MapSeat.sort_order, Ticket.code)
    ):
        tickets[t.order_id].append({"code": t.code, "tierId": t.tier_id, "name": name, "price": t.price,
                                    "seat": seat_label, "checkedInAt": iso_vn(t.checked_in_at)})

    out = []
    for o in orders:
        ev, show = events[o.event_id], shows[(o.event_id, o.show_id)]
        out.append({
            "id": o.id, "slug": ev.slug, "title": ev.title, "showId": o.show_id,
            "start": iso_vn(show.starts_at), "startTime": hhmm(show.starts_at), "endTime": hhmm(show.end_time),
            "venue": ev.venue, "address": ev.address, "items": items[o.id], "tickets": tickets[o.id],
            "subtotal": o.subtotal, "discount": o.discount, "coupon": o.coupon_code, "total": o.total,
            "method": o.method, "status": o.status, "refundedAt": iso_vn(o.refunded_at),
            "eventStatus": ev.status, "cancelReason": ev.cancel_reason, "cancelledBy": ev.cancelled_by,
            "buyer": {"name": o.buyer_name, "email": o.buyer_email, "phone": o.buyer_phone},
            "createdAt": iso_vn(o.created_at),
        })
    return out


def user_orders(db: Session, user_id: int) -> list[dict]:
    rows = db.scalars(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc(), Order.id.desc()))
    return orders_json(db, list(rows))


# ---------------------------------------------------------------- tạo đơn
# OrderIn chuyển sang app/schemas (body request) — giữ tên ở đây cho mã cũ
def _qty(v: Any) -> int | None:
    """Giống Number(v) + Number.isInteger của Node: 2, "2", 2.0 hợp lệ; 1.5, true, "abc" không"""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else None
    if isinstance(v, str):
        try:
            f = float(v.strip())
        except ValueError:
            return None
        return int(f) if f.is_integer() else None
    return None


def _vnd(n: int) -> str:
    """500000 → "500.000" (định dạng vi-VN)"""
    return f"{n:,}".replace(",", ".")


def _tier_lines(db: Session, ev: Event, raw_items: Any) -> list[tuple[TicketTier, int]]:
    wanted: dict[str, int] = {}
    for it in raw_items if isinstance(raw_items, list) else []:
        qty = _qty(it.get("qty")) if isinstance(it, dict) else None
        if qty is None or qty <= 0:
            raise HTTPException(400, "Số lượng vé không hợp lệ")
        tid = as_str(it.get("tierId"))
        wanted[tid] = wanted.get(tid, 0) + qty
    if not wanted:
        raise HTTPException(400, "Vui lòng chọn ít nhất 1 vé")
    tiers = {t.id: t for t in db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.active))}
    lines = []
    for tid, qty in wanted.items():
        tier = tiers.get(tid)
        if tier is None:
            raise HTTPException(400, "Hạng vé không hợp lệ")
        if qty > tier.max_per_order:
            raise HTTPException(400, f"{tier.name}: tối đa {tier.max_per_order} vé mỗi đơn")
        lines.append((tier, qty))
    return lines


def _take_stock(db: Session, ev: Event, show: Show, lines: list[tuple[TicketTier, int]]) -> None:
    """Trừ kho NGUYÊN TỬ: UPDATE chỉ thành công khi còn đủ vé (presold + sold + qty <= capacity).
    Khoá dòng theo thứ tự tier_id để hai đơn mua chéo hạng vé không deadlock.
    Thất bại ở bất kỳ hạng nào → HTTPException; router rollback cả đơn (không trừ kho một phần)."""
    for tier, qty in sorted(lines, key=lambda line: line[0].id):
        key = (TierStock.event_id == ev.id, TierStock.show_id == show.id, TierStock.tier_id == tier.id)
        # Sự kiện của Ban tổ chức có thể chưa có dòng kho: tạo với sức chứa của hạng vé
        db.execute(insert(TierStock).values(event_id=ev.id, show_id=show.id, tier_id=tier.id,
                                            capacity=tier.capacity, presold=0, sold=0).on_conflict_do_nothing())
        taken = db.execute(
            update(TierStock)
            .where(*key, TierStock.presold + TierStock.sold + qty <= TierStock.capacity)
            .values(sold=TierStock.sold + qty)
            .returning(TierStock.tier_id)
        ).first()
        if taken is None:
            left = max(0, db.scalar(select(TierStock.capacity - TierStock.presold - TierStock.sold).where(*key)) or 0)
            raise HTTPException(409, f"{tier.name} chỉ còn {left} vé" if left else f"{tier.name} vừa hết vé")


def _seat_taken(seat: MapSeat) -> HTTPException:
    return HTTPException(409, f"Ghế {seat.row_label}{seat.num} ({seat.label}) vừa có người mua")


def _seat_lines(db: Session, ev: Event, show: Show, raw_seats: Any):
    """Ghế yêu cầu → [(hạng vé, số ghế)] và {hạng vé: [mã ghế]} (giữ thứ tự yêu cầu)"""
    ids = list(dict.fromkeys(as_str(s) for s in raw_seats)) if isinstance(raw_seats, list) else []
    if not ids:
        raise HTTPException(400, "Vui lòng chọn ít nhất 1 ghế")
    if len(ids) > MAX_PER_ORDER:
        raise HTTPException(400, f"Mỗi đơn tối đa {MAX_PER_ORDER} vé")
    seats = {s.id: s for s in db.scalars(select(MapSeat).where(MapSeat.map_id == ev.map_id, MapSeat.id.in_(ids)))}
    if any(i not in seats for i in ids):
        raise HTTPException(400, "Ghế không hợp lệ")
    held = set(db.scalars(select(SeatHold.seat_id).where(SeatHold.event_id == ev.id, SeatHold.show_id == show.id,
                                                         SeatHold.seat_id.in_(ids))))
    for i in ids:
        if i in held:
            raise _seat_taken(seats[i])
    tiers = {t.id: t for t in db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.active))}
    by_tier: dict[str, list[str]] = {}
    for i in ids:
        group = seats[i].group_id
        if group not in tiers:
            raise HTTPException(400, "Hạng vé không hợp lệ")
        by_tier.setdefault(group, []).append(i)
    return [(tiers[g], len(v)) for g, v in by_tier.items()], by_tier


def _hold_seats(db: Session, ev: Event, show: Show, order: Order, seats_by_tier: dict[str, list[str]]) -> None:
    """Giữ ghế NGUYÊN TỬ: INSERT … ON CONFLICT DO NOTHING RETURNING.
    Ghế nào không được trả về = vừa có người khác giữ (khoá chính chặn trùng) → 409, router rollback cả đơn."""
    wanted = [s for ids in seats_by_tier.values() for s in ids]
    # Chèn theo thứ tự mã ghế CỐ ĐỊNH: hai đơn [A,B] và [B,A] luôn tranh ghế A trước → không deadlock
    got = set(db.scalars(
        insert(SeatHold)
        .values([{"event_id": ev.id, "show_id": show.id, "seat_id": s, "order_id": order.id} for s in sorted(wanted)])
        .on_conflict_do_nothing()
        .returning(SeatHold.seat_id)
    ))
    lost = next((s for s in wanted if s not in got), None)
    if lost is not None:
        raise _seat_taken(db.get(MapSeat, (ev.map_id, lost)))


def _discount(db: Session, raw_code: Any, subtotal: int) -> tuple[int, str | None]:
    code = as_str(raw_code).strip().upper()
    if not code:
        return 0, None
    c = db.scalar(select(Coupon).where(func.upper(Coupon.code) == code, Coupon.active))
    if c is None:
        raise HTTPException(400, "Mã giảm giá không tồn tại")
    if subtotal < c.min_order:
        raise HTTPException(400, f"Mã {c.code} chỉ áp dụng cho đơn từ {_vnd(c.min_order)} ₫")
    return min(c.amount, subtotal), c.code


def _new_ticket_codes(db: Session, n: int) -> list[str]:
    codes: list[str] = []
    while len(codes) < n:
        code = new_ticket_code(db)
        if code not in codes:
            codes.append(code)
    return codes


def create_order(db: Session, user: User, body: OrderIn) -> Order:
    """Tạo đơn trong transaction hiện tại (router commit / rollback).
    Kiểm tra theo đúng thứ tự của bản Node; trừ kho / giữ ghế sau cùng."""
    ev = db.scalar(public_events_query().where(Event.slug == as_str(body.slug)))
    if ev is None:
        raise HTTPException(404, "Sự kiện không tồn tại")
    now = datetime.now(timezone.utc)
    if ev.sale_start is not None and ev.sale_start > now:
        raise HTTPException(400, "Sự kiện chưa mở bán")
    shows = db.scalars(select(Show).where(Show.event_id == ev.id, Show.active).order_by(Show.starts_at, Show.id)).all()
    sid = as_str(body.showId)
    show = next((s for s in shows if s.id == sid), None) if sid else (shows[0] if shows else None)
    if show is None:
        raise HTTPException(400, "Suất diễn không hợp lệ")
    if show.starts_at <= now:
        raise HTTPException(400, "Suất diễn này đã diễn ra")

    buyer = body.buyer if isinstance(body.buyer, dict) else {}
    buyer_name = as_str(buyer.get("name")).strip()
    buyer_email = as_str(buyer.get("email")).strip().lower()
    if not 2 <= len(buyer_name) <= 80:
        raise HTTPException(400, "Vui lòng nhập họ tên người nhận vé")
    if not is_email(buyer_email):
        raise HTTPException(400, "Email nhận vé không hợp lệ")
    if not is_phone(buyer.get("phone")):
        raise HTTPException(400, "Số điện thoại không hợp lệ")
    method = as_str(body.method)
    if method not in PAYMENT_METHODS:
        raise HTTPException(400, "Phương thức thanh toán không hợp lệ")

    if ev.layout == "seats":
        lines, seats_by_tier = _seat_lines(db, ev, show, body.seats)
    else:
        lines, seats_by_tier = _tier_lines(db, ev, body.items), {}
    if sum(q for _, q in lines) > MAX_PER_ORDER:
        raise HTTPException(400, f"Mỗi đơn tối đa {MAX_PER_ORDER} vé")
    subtotal = sum(t.price * q for t, q in lines)
    discount, coupon = _discount(db, body.coupon, subtotal)

    order = Order(id=new_order_id(db), user_id=user.id, event_id=ev.id, show_id=show.id, subtotal=subtotal,
                  discount=discount, coupon_code=coupon, total=subtotal - discount, method=method,
                  buyer_name=buyer_name, buyer_email=buyer_email, buyer_phone=normalize_phone(buyer.get("phone")))
    db.add(order)
    db.flush()

    if ev.layout == "seats":
        _hold_seats(db, ev, show, order, seats_by_tier)
    else:
        _take_stock(db, ev, show, lines)

    codes = iter(_new_ticket_codes(db, sum(q for _, q in lines)))
    for tier, qty in lines:
        db.add(OrderItem(order_id=order.id, event_id=ev.id, tier_id=tier.id, price=tier.price, qty=qty))
        seat_ids = seats_by_tier.get(tier.id) or [None] * qty
        for seat_id in seat_ids:
            db.add(Ticket(code=next(codes), order_id=order.id, event_id=ev.id, tier_id=tier.id, price=tier.price,
                          seat_id=seat_id))
    db.flush()
    return order

