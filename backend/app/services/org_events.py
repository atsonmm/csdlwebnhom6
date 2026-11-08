"""Sửa / huỷ sự kiện của Ban tổ chức (dùng chung với Admin ở Task D4)"""
from datetime import time as dtime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session

from app.middlewares.errors import not_found
from app.models.catalog import Event, MapGroup, Show, TicketTier
from app.models.sales import Order, OrderItem, TierStock
from app.config.rules import TIER_MAX_PER_ORDER
from app.services.stock import tier_stats
from app.utils.textnorm import search_text_for
from app.utils.timefmt import VN, hhmm
from app.services import manage
from app.utils.validators import as_str

REASON_MSG = "Vui lòng nhập lý do huỷ (5–300 ký tự)"
ALREADY_CANCELLED = "Sự kiện đã được huỷ trước đó"
ALREADY_HAPPENED = "Sự kiện đã diễn ra, không thể huỷ"


def _after_lock() -> None:
    """Móc chạy ngay sau khi khoá dòng sự kiện — mặc định không làm gì; test đồng thời dùng để giữ khoá"""


def _lock_event(db: Session, organizer_id: int | None, event_id: int) -> Event:
    """SELECT … FOR UPDATE: hai yêu cầu huỷ/sửa cùng sự kiện xếp hàng, bên sau thấy trạng thái mới của bên trước"""
    q = select(Event).where(Event.id == event_id).with_for_update()
    if organizer_id is not None:
        q = q.where(Event.organizer_id == organizer_id)
    ev = db.scalar(q)
    if ev is None:
        raise not_found(manage.EVENT_NOT_FOUND)
    _after_lock()
    return ev


def _refund_paid_orders(db: Session, event_id: int) -> tuple[int, int]:
    """Mọi đơn 'paid' của sự kiện → 'refunded' (một câu UPDATE); trả về (số đơn, tổng tiền hoàn)"""
    totals = db.scalars(update(Order).where(Order.event_id == event_id, Order.status == "paid")
                        .values(status="refunded", refunded_at=func.now()).returning(Order.total)).all()
    return len(totals), sum(totals)


def cancel_event(db: Session, organizer_id: int | None, event_id: int, reason: Any, by: str = "organizer") -> dict:
    """Huỷ sự kiện. Chưa có đơn nào → xoá hẳn (chỉ BTC). Có đơn → status 'cancelled' + hoàn mọi đơn đã trả.
    Cả hai bước nằm trong transaction của người gọi (router commit một lần) — lỗi giữa chừng thì không ghi gì."""
    ev = _lock_event(db, organizer_id, event_id)
    if ev.status == "cancelled":
        raise HTTPException(409, ALREADY_CANCELLED)
    last_start = db.scalar(select(func.max(Show.starts_at)).where(Show.event_id == ev.id))
    if manage.phase_of(ev, last_start, manage.now_utc()) in ("closed", "ended"):
        raise HTTPException(409, ALREADY_HAPPENED)

    has_orders = db.scalar(select(exists().where(Order.event_id == ev.id)))
    if not has_orders and by == "organizer":
        db.execute(delete(Event).where(Event.id == ev.id))  # cascade: suất, hạng vé, kho, home_slots
        return {"deleted": True}

    text = as_str(reason).strip() if isinstance(reason, str) else ""
    if not 5 <= len(text) <= 300:
        raise HTTPException(400, REASON_MSG)
    ev.status, ev.cancel_reason, ev.cancelled_by = "cancelled", text, by
    ev.cancelled_at = func.now()
    db.flush()
    n, amount = _refund_paid_orders(db, ev.id)
    db.refresh(ev)
    return {"deleted": False, "refundedOrders": n, "refundedAmount": amount, "event": manage.event_summaries(db, [ev])[0]}


# ---------------------------------------------------------------- sửa sự kiện (Task D2)
NOT_EDITABLE = "Sự kiện này không còn sửa được"
LOCKED_LABEL = {"title": "tên sự kiện", "category": "danh mục", "city": "thành phố", "venue": "địa điểm",
                "date": "ngày diễn", "startTime": "giờ bắt đầu", "endTime": "giờ kết thúc"}


def update_event(db: Session, organizer_id: int, event_id: int, body: manage.OrgEventIn) -> Event:
    """Sửa sự kiện theo mức editable: full (chưa duyệt) thay toàn bộ; limited (đã duyệt, chưa diễn) chỉ đổi phần
    không ảnh hưởng người đã mua; none → 409. Khoá sự kiện + dòng kho FOR UPDATE trước khi đọc số đã bán."""
    ev = _lock_event(db, organizer_id, event_id)
    show = db.scalars(select(Show).where(Show.event_id == ev.id).order_by(Show.starts_at, Show.id)).first()
    last_start = db.scalar(select(func.max(Show.starts_at)).where(Show.event_id == ev.id))
    mode = manage.editable_of(ev, manage.phase_of(ev, last_start, manage.now_utc()))["mode"]
    if mode == "none":
        raise HTTPException(409, NOT_EDITABLE)
    if mode == "limited":  # đã duyệt: người mua đã dựa vào kiểu bán / sơ đồ → khoá (kiểm trước khi kiểm form)
        if (as_str(body.layout).strip() or "list") != ev.layout:
            raise HTTPException(409, "Sự kiện đã duyệt không thể đổi kiểu bán vé")
        if ev.layout != "list" and body.mapId != ev.map_id:
            raise HTTPException(409, "Sự kiện đã duyệt không thể đổi sơ đồ")
    v = manage.validate_event_form(db, body)
    db.execute(select(TierStock.tier_id).where(TierStock.event_id == ev.id).with_for_update())  # khoá kho
    if mode == "full":
        _full_edit(db, ev, v)
    else:
        _limited_edit(db, ev, show, v)
    db.flush()
    db.refresh(ev)
    return ev


def _apply_common(ev: Event, v: dict) -> None:
    ev.address = v["address"] or f"[ĐỊA CHỈ], {v['city']}"
    ev.description = v["description_paras"]


def _full_edit(db: Session, ev: Event, v: dict) -> None:
    """Chưa duyệt → chưa thể có đơn: thay suất / hạng vé / kho mới hoàn toàn"""
    ev.title, ev.category_id, ev.city, ev.venue = v["title"], v["category"].id, v["city"], v["venue"]
    ev.search_text = search_text_for(v["title"], v["city"], v["venue"], v["category"].label)
    ev.sale_start = v["sale_start"]
    _apply_common(ev, v)
    ev.layout, ev.map_id = v["layout"], v["map_id"]  # Task F4: đổi được kiểu bán / sơ đồ khi chưa duyệt
    if ev.status == "rejected":
        ev.status, ev.reject_reason, ev.reviewed_at = "pending", None, None
    db.execute(delete(Show).where(Show.event_id == ev.id))  # cascade: kho của suất cũ
    db.execute(delete(TicketTier).where(TicketTier.event_id == ev.id))
    db.flush()
    sid = manage.show_id_for(v["day"], v["start"])
    db.add(Show(event_id=ev.id, id=sid, starts_at=v["show_start"], end_time=dtime.fromisoformat(v["end"])))
    for t in v["tiers"]:
        db.add(TicketTier(event_id=ev.id, **manage.tier_columns(t)))
    db.flush()
    if v["layout"] != "seats":  # bán theo ghế: không có dòng kho (đã bán = seat_holds)
        db.add_all([TierStock(event_id=ev.id, show_id=sid, tier_id=t["id"], capacity=t["capacity"], presold=0, sold=0)
                    for t in v["tiers"]])


def _limited_edit(db: Session, ev: Event, show: Show, v: dict) -> None:
    """Đã duyệt, chưa diễn: không đổi thông tin người mua đã dựa vào; không bán dưới số đã bán"""
    old = {"title": ev.title, "category": ev.category_id, "city": ev.city, "venue": ev.venue,
           "date": show.starts_at.astimezone(VN).date().isoformat(), "startTime": hhmm(show.starts_at),
           "endTime": hhmm(show.end_time)}
    new = {"title": v["title"], "category": v["category"].id, "city": v["city"], "venue": v["venue"],
           "date": v["day"].isoformat(), "startTime": v["start"], "endTime": v["end"]}
    for field, label in LOCKED_LABEL.items():
        if old[field] != new[field]:
            raise HTTPException(409, f"Sự kiện đã duyệt không thể đổi {label}")
    if v["sale_start"] != ev.sale_start:
        opens = manage.sale_opens_at(ev)
        if opens is not None and opens <= manage.now_utc():
            raise HTTPException(409, "Đã mở bán, không đổi được giờ mở bán")
        if v["sale_start"] is not None and v["sale_start"] <= manage.now_utc():
            raise HTTPException(400, "Giờ mở bán phải sau thời điểm hiện tại")
        ev.sale_start = v["sale_start"]
    _apply_common(ev, v)
    if ev.layout != "list":
        _limited_map_prices(db, ev, v)
        return

    tiers = {t.id: t for t in db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.active))}
    sold = {tid: st.presold + st.sold for (_e, tid), st in tier_stats(db, [ev]).items()}
    kept: set[str] = set()
    fresh: list[dict] = []
    for i, t in enumerate(v["tiers"], start=1):
        tid = t["given_id"]
        if tid is None:
            fresh.append(t | {"sort_order": i})
            continue
        if tid not in tiers or tid in kept:
            raise HTTPException(400, "Loại vé không hợp lệ")
        kept.add(tid)
        row, n = tiers[tid], sold.get(tid, 0)
        if t["capacity"] < n:
            raise HTTPException(400, f"Loại vé “{t['name']}”: không thể ít hơn {n} vé đã bán")
        if t["price"] != row.price and n > 0:
            raise HTTPException(409, f"Loại vé “{row.name}” đã có người mua, không đổi được giá")
        row.name, row.price, row.perks, row.capacity, row.sort_order = t["name"], t["price"], t["perks"], t["capacity"], i
        db.execute(update(TierStock).where(TierStock.event_id == ev.id, TierStock.tier_id == tid)
                   .values(capacity=t["capacity"]))
    for tid, row in tiers.items():
        if tid in kept:
            continue
        has_items = db.scalar(select(exists().where(OrderItem.event_id == ev.id, OrderItem.tier_id == tid)))
        if sold.get(tid, 0) > 0 or has_items:
            raise HTTPException(409, f"Loại vé “{row.name}” đã có người mua, không bỏ được")
        db.execute(delete(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.id == tid))
    if fresh:
        all_ids = db.scalars(select(TicketTier.id).where(TicketTier.event_id == ev.id)).all()
        nxt = max([int(x[3:]) for x in all_ids if x.startswith("ve-") and x[3:].isdigit()] + [0]) + 1
        shows = db.scalars(select(Show.id).where(Show.event_id == ev.id)).all()
        for t in fresh:
            tid = f"ve-{nxt}"
            nxt += 1
            db.add(TicketTier(event_id=ev.id, **(manage.tier_columns(t) | {"id": tid})))
            db.flush()
            db.add_all([TierStock(event_id=ev.id, show_id=sid, tier_id=tid, capacity=t["capacity"], presold=0, sold=0)
                        for sid in shows])


def _limited_map_prices(db: Session, ev: Event, v: dict) -> None:
    """Sự kiện theo sơ đồ đã duyệt: chỉ đổi giá của NHÓM chưa bán vé nào; không thêm/bỏ hạng, không đổi sức chứa
    (sức chứa do sơ đồ quyết định). Nhóm đã bán (kể cả bán sẵn) mà đổi giá → 409."""
    tiers = db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.active)
                       .order_by(TicketTier.sort_order, TicketTier.id)).all()
    sold = {tid: st.presold + st.sold for (_e, tid), st in tier_stats(db, [ev]).items()}
    group_sold: dict[str, int] = {}
    for t in tiers:
        g = t.group_id or t.id
        group_sold[g] = group_sold.get(g, 0) + sold.get(t.id, 0)
    labels = dict(db.execute(select(MapGroup.id, MapGroup.label).where(MapGroup.map_id == ev.map_id)).all())
    new_price = {t["id"]: t["price"] for t in v["tiers"]}
    for t in tiers:
        price = new_price.get(t.id)
        if price is None or price == t.price:
            continue
        g = t.group_id or t.id
        if group_sold.get(g, 0) > 0:
            raise HTTPException(409, f"Nhóm “{labels.get(g, g)}” đã có người mua, không đổi được giá")
        t.price = price
