"""Ban tổ chức & Quản trị sàn — giống server/manage.js của bản Node"""
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import exists, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.catalog import Category, Event, Show, TicketTier
from app.models.sales import Order, OrderItem, Ticket, TierStock
from app.models.users import Organizer, User
from app.schemas.manage import OrgEventIn  # noqa: F401  (body request, dùng lại tên manage.OrgEventIn)
from app.config.rules import TIER_MAX_PER_ORDER
from app.services.stock import tier_stats
from app.utils.textnorm import search_text_for, slugify
from app.utils.timefmt import VN, hhmm, iso_vn
from app.utils.validators import as_str, is_phone, normalize_phone


def unique_slug(db: Session, title: str) -> str:
    """Slug chưa dùng (kể cả so với sự kiện có sẵn của sàn): base, base-2, base-3…"""
    base = slugify(title) or "su-kien"
    slug, i = base, 2
    while db.scalar(select(exists().where(Event.slug == slug))):
        slug, i = f"{base}-{i}", i + 1
    return slug


def event_summaries(db: Session, events: list[Event]) -> list[dict]:
    """Tóm tắt sự kiện kèm số vé đã bán + doanh thu (chỉ đơn đã thanh toán), truy vấn theo lô"""
    if not events:
        return []
    ids = [e.id for e in events]
    org_names = dict(db.execute(select(Organizer.user_id, Organizer.org_name).where(
        Organizer.user_id.in_({e.organizer_id for e in events if e.organizer_id is not None}))).all())
    first_show: dict[int, Show] = {}
    last_show: dict[int, Show] = {}
    for s in db.scalars(select(Show).where(Show.event_id.in_(ids)).order_by(Show.starts_at, Show.id)):
        first_show.setdefault(s.event_id, s)
        last_show[s.event_id] = s
    now = now_utc()
    min_price = dict(db.execute(select(TicketTier.event_id, func.min(TicketTier.price))
                                .where(TicketTier.event_id.in_(ids), TicketTier.active).group_by(TicketTier.event_id)).all())
    # Sức chứa / đã bán (kể cả bán sẵn) qua kho chung — khớp "còn lại" khách thấy
    stock: dict[int, list[int]] = {}
    for (eid, _tid), st in tier_stats(db, events).items():
        a = stock.setdefault(eid, [0, 0])
        a[0] += st.capacity
        a[1] += st.presold + st.sold
    paid = Order.status == "paid"
    revenue = dict(db.execute(select(Order.event_id, func.sum(Order.total))
                              .where(Order.event_id.in_(ids), paid).group_by(Order.event_id)).all())
    out = []
    for e in events:
        show = first_show.get(e.id)
        cap, sold = stock.get(e.id, (0, 0))
        out.append({
            "id": e.id, "slug": e.slug, "title": e.title, "category": e.category_id, "city": e.city, "venue": e.venue,
            "date": show.starts_at.astimezone(VN).date().isoformat() if show else None,
            "startTime": hhmm(show.starts_at) if show else None,
            "status": e.status, "rejectReason": e.reject_reason, "orgName": org_names.get(e.organizer_id),
            "createdAt": iso_vn(e.created_at), "capacity": cap, "minPrice": int(min_price.get(e.id) or 0),
            "sold": sold, "revenue": int(revenue.get(e.id, 0)),
            "phase": phase_of(e, last_show[e.id].starts_at if e.id in last_show else None, now),
            "cancelReason": e.cancel_reason, "cancelledBy": e.cancelled_by,
            "saleOpensAt": iso_vn(sale_opens_at(e)), "reviewedAt": iso_vn(e.reviewed_at),
        })
    return out


# ---------------------------------------------------------------- Ban tổ chức
def register_organizer(db: Session, user: User, org_name_raw: Any, phone_raw: Any, description_raw: Any) -> User:
    if user.role == "admin":
        raise HTTPException(400, "Tài khoản quản trị không thể đăng ký làm Ban tổ chức")
    org_name = as_str(org_name_raw).strip()
    phone = as_str(phone_raw).strip()
    description = as_str(description_raw).strip()
    if not 2 <= len(org_name) <= 120:
        raise HTTPException(400, "Vui lòng nhập tên đơn vị tổ chức (2–120 ký tự)")
    if not is_phone(phone):
        raise HTTPException(400, "Số điện thoại liên hệ không hợp lệ")
    if len(description) > 1000:
        raise HTTPException(400, "Giới thiệu tối đa 1000 ký tự")
    stmt = insert(Organizer).values(user_id=user.id, org_name=org_name, phone=normalize_phone(phone),
                                    description=description)
    db.execute(stmt.on_conflict_do_update(index_elements=["user_id"], set_={
        "org_name": stmt.excluded.org_name, "phone": stmt.excluded.phone, "description": stmt.excluded.description}))
    user.role = "organizer"
    db.flush()
    return user


def _recent_orders(db: Session, organizer_id: int, limit: int = 6, event_id: int | None = None) -> list[dict]:
    stmt = (select(Order, User.name).join(Event, Event.id == Order.event_id).join(User, User.id == Order.user_id)
            .where(Event.organizer_id == organizer_id, Order.status == "paid"))  # đơn đã hoàn / huỷ không phải tiền vào
    if event_id is not None:
        stmt = stmt.where(Order.event_id == event_id)
    rows = db.execute(stmt.order_by(Order.created_at.desc(), Order.id.desc()).limit(limit)).all()
    ids = [o.id for o, _ in rows]
    items: dict[str, list[str]] = {i: [] for i in ids}
    for it, name in db.execute(
        select(OrderItem, TicketTier.name)
        .join(TicketTier, (TicketTier.event_id == OrderItem.event_id) & (TicketTier.id == OrderItem.tier_id))
        .where(OrderItem.order_id.in_(ids)).order_by(TicketTier.sort_order, TicketTier.id)
    ):
        items[it.order_id].append(f"{name} ×{it.qty}")
    # Khoá created_at (snake_case) giữ đúng như API Node — OrganizerDashboard đọc r.created_at
    return [{"id": o.id, "total": o.total, "created_at": iso_vn(o.created_at), "name": name, "items": ", ".join(items[o.id])}
            for o, name in rows]


def organizer_dashboard(db: Session, user: User) -> dict:
    org = db.get(Organizer, user.id)
    first_start = (select(func.min(Show.starts_at)).where(Show.event_id == Event.id).correlate(Event).scalar_subquery())
    events = db.scalars(select(Event).where(Event.organizer_id == user.id).order_by(first_start, Event.id)).all()
    return {
        "organizer": {"orgName": org.org_name if org else None, "phone": org.phone if org else None,
                      "description": org.description if org else None,
                      "createdAt": iso_vn(org.created_at) if org else None, "code": f"ORG-{user.id:05d}"},
        "events": event_summaries(db, list(events)),
        "recentOrders": _recent_orders(db, user.id),
    }


# ---------------------------------------------------------------- tạo sự kiện
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DEFAULT_REJECT_REASON = "Hồ sơ chưa đủ thông tin, vui lòng bổ sung."


def now_utc() -> datetime:
    """Tách riêng để test đóng băng thời gian"""
    return datetime.now(timezone.utc)


def _int(v: Any) -> int | None:
    """Giống Number(v) + Number.isInteger của Node: 200000, "200000", 2e5 hợp lệ; 1.5, "abc", true không"""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v
    try:
        f = float(v.strip() if isinstance(v, str) else v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else None


# OrgEventIn chuyển sang app/schemas (body request) — giữ tên ở đây cho mã cũ
def _validated_tiers(raw: Any) -> list[dict]:
    items = raw if isinstance(raw, list) else []
    if not 1 <= len(items) <= 8:
        raise HTTPException(400, "Cần từ 1 đến 8 loại vé")
    out = []
    for i, t in enumerate(items, start=1):
        t = t if isinstance(t, dict) else {}
        name = as_str(t.get("name")).strip()
        if not 1 <= len(name) <= 60:
            raise HTTPException(400, f"Loại vé {i}: vui lòng nhập tên")
        price, quantity = _int(t.get("price")), _int(t.get("quantity"))
        if price is None or not 10_000 <= price <= 100_000_000:
            raise HTTPException(400, f"Loại vé “{name}”: giá từ 10.000 ₫ đến 100.000.000 ₫")
        if quantity is None or not 1 <= quantity <= 100_000:
            raise HTTPException(400, f"Loại vé “{name}”: số lượng từ 1 đến 100.000")
        given = t.get("id")
        out.append({"id": f"ve-{i}", "name": name, "price": price, "capacity": quantity,
                    "perks": as_str(t.get("perks")).strip()[:200], "sort_order": i,
                    "given_id": given if isinstance(given, str) and given else None})
    return out


def validate_event_form(db: Session, body: OrgEventIn) -> dict:
    """Kiểm tra form tạo / sửa sự kiện (dùng chung) → giá trị đã chuẩn hoá; sai → 400"""
    layout = as_str(body.layout).strip() or "list"
    if layout not in ("list", "zones", "seats"):
        raise HTTPException(400, "Kiểu bán vé không hợp lệ")
    title = as_str(body.title).strip()
    category = as_str(body.category)
    city = as_str(body.city).strip()
    venue = as_str(body.venue).strip()
    address = as_str(body.address).strip()
    date_s, start_s, end_s = as_str(body.date), as_str(body.startTime), as_str(body.endTime)
    description = as_str(body.description).strip()

    if not 3 <= len(title) <= 120:
        raise HTTPException(400, "Tên sự kiện cần từ 3 đến 120 ký tự")
    cat = db.get(Category, category) if category else None
    if cat is None:
        raise HTTPException(400, "Danh mục không hợp lệ")
    if not 2 <= len(city) <= 60:
        raise HTTPException(400, "Vui lòng nhập thành phố")
    if not 2 <= len(venue) <= 120:
        raise HTTPException(400, "Vui lòng nhập địa điểm tổ chức")
    if len(address) > 200:
        raise HTTPException(400, "Địa chỉ tối đa 200 ký tự")
    try:
        day = date.fromisoformat(date_s) if DATE_RE.match(date_s) else None
    except ValueError:
        day = None
    if day is None:
        raise HTTPException(400, "Ngày diễn không hợp lệ")
    if day < now_utc().astimezone(VN).date():  # so theo NGÀY giờ Việt Nam
        raise HTTPException(400, "Ngày diễn phải từ hôm nay trở đi")
    if not TIME_RE.match(start_s) or not TIME_RE.match(end_s):
        raise HTTPException(400, "Giờ bắt đầu / kết thúc không hợp lệ")
    if end_s <= start_s:
        raise HTTPException(400, "Giờ kết thúc phải sau giờ bắt đầu")
    show_start = datetime.combine(day, time.fromisoformat(start_s), tzinfo=VN)
    sale_start = parse_sale_start(body.saleStart, show_start)
    if not 20 <= len(description) <= 4000:
        raise HTTPException(400, "Giới thiệu sự kiện cần từ 20 đến 4000 ký tự")
    if layout == "list":
        tiers, map_id = _validated_tiers(body.tiers), None
    else:
        from app.services import org_maps  # import muộn: org_maps dùng manage._int

        tiers, map_id = org_maps.tiers_for_map(db, layout, body.mapId, body.prices), body.mapId
    return {"layout": layout, "map_id": map_id, "title": title, "category": cat, "city": city, "venue": venue, "address": address, "day": day,
            "start": start_s, "end": end_s, "show_start": show_start, "sale_start": sale_start,
            "description_paras": [p.strip() for p in re.split(r"\n\s*\n", description) if p.strip()], "tiers": tiers}


def show_id_for(day: date, start: str) -> str:
    return f"{day.isoformat().replace('-', '')}-{start.replace(':', '')}"


def tier_columns(t: dict) -> dict:
    """Dòng hạng vé đã kiểm tra → cột của ticket_tiers (bỏ khoá phụ given_id); hạng theo sơ đồ có group_id và
    giới hạn mỗi đơn của nhóm, hạng tự đặt dùng TIER_MAX_PER_ORDER"""
    return {**{k: t[k] for k in ("id", "name", "price", "capacity", "perks", "sort_order")},
            "group_id": t.get("group_id"), "max_per_order": t.get("max_per_order") or TIER_MAX_PER_ORDER}


def create_org_event(db: Session, user: User, body: OrgEventIn) -> Event:
    """Sự kiện mới của Ban tổ chức → chờ sàn duyệt. Tạo luôn suất diễn, hạng vé ve-N và dòng kho."""
    v = validate_event_form(db, body)
    title, cat, city, venue, address = v["title"], v["category"], v["city"], v["venue"], v["address"]
    day, start_s, end_s, sale_start, tiers = v["day"], v["start"], v["end"], v["sale_start"], v["tiers"]

    # Khoá theo slug gốc tới hết transaction: hai yêu cầu tạo cùng tên (bấm đúp, gửi lại) xếp hàng
    # thay vì cùng thấy slug còn trống rồi va nhau ở ràng buộc UNIQUE (lỗi 500)
    db.execute(select(func.pg_advisory_xact_lock(func.hashtext(slugify(title) or "su-kien"))))
    ev = Event(slug=unique_slug(db, title), title=title, search_text=search_text_for(title, city, venue, cat.label),
               category_id=cat.id, city=city, venue=venue, address=address or f"[ĐỊA CHỈ], {city}", layout=v["layout"],
               map_id=v["map_id"], organizer_id=user.id, description=v["description_paras"], notes=[], status="pending", sale_start=sale_start)
    db.add(ev)
    db.flush()
    show_id = show_id_for(day, start_s)
    db.add(Show(event_id=ev.id, id=show_id, starts_at=datetime.combine(day, time.fromisoformat(start_s), tzinfo=VN),
                end_time=time.fromisoformat(end_s)))
    for t in tiers:
        db.add(TicketTier(event_id=ev.id, **tier_columns(t)))
    db.flush()
    if v["layout"] != "seats":  # bán theo ghế: đã bán = seat_holds, không có dòng kho
        db.add_all([TierStock(event_id=ev.id, show_id=show_id, tier_id=t["id"], capacity=t["capacity"], presold=0,
                              sold=0) for t in tiers])
    db.flush()
    return ev


# ---------------------------------------------------------------- Quản trị sàn
def overview(db: Session) -> dict:
    pending = db.scalars(select(Event).where(Event.organizer_id.is_not(None), Event.status == "pending")
                         .order_by(Event.created_at, Event.id)).all()
    ticket_count = (select(func.count()).select_from(Ticket).where(Ticket.order_id == Order.id)
                    .correlate(Order).scalar_subquery())
    recent = db.execute(
        select(Order, Event.title, User.name, ticket_count)
        .join(Event, Event.id == Order.event_id).join(User, User.id == Order.user_id)
        .order_by(Order.created_at.desc(), Order.id.desc()).limit(10)
    ).all()

    def count(stmt) -> int:
        return int(db.scalar(stmt) or 0)

    paid = Order.status == "paid"
    per_event = db.execute(select(Event.organizer_id.is_not(None), func.sum(Order.total))
                           .join(Event, Event.id == Order.event_id).where(paid).group_by(Event.id)).all()
    org_revenue = [int(r) for is_org, r in per_event if is_org]
    platform_revenue = sum(int(r) for is_org, r in per_event if not is_org)
    from app.models.payouts import Withdrawal  # import muộn: payouts không phụ thuộc manage

    return {
        "pendingWithdrawals": count(select(func.count()).select_from(Withdrawal).where(Withdrawal.status == "pending")),
        "pending": event_summaries(db, list(pending)),
        "orders": [{"id": o.id, "event": title, "amount": o.total, "status": o.status, "createdAt": iso_vn(o.created_at),
                    "customer": name, "tickets": int(n)} for o, title, name, n in recent],
        "totals": {
            "revenue": sum(org_revenue) + platform_revenue,
            "orgRevenue": sum(org_revenue),
            "platformRevenue": platform_revenue,  # sự kiện sàn tự bán — không tính phí
            "fee": sum(fee_of(r) for r in org_revenue),
            "orders": count(select(func.count()).select_from(Order).where(paid)),
            "tickets": count(select(func.count()).select_from(Ticket).join(Order, Order.id == Ticket.order_id).where(paid)),
            "customers": count(select(func.count()).select_from(User).where(User.role == "customer")),
            "organizers": count(select(func.count()).select_from(Organizer)),
            "approvedEvents": count(select(func.count()).select_from(Event).where(
                Event.organizer_id.is_not(None), Event.status == "approved")),
        },
    }


REVIEW_NOT_FOUND = "Không tìm thấy hồ sơ sự kiện"


ORGANIZER_NOT_FOUND = "Không tìm thấy ban tổ chức"
LIVE_PHASES = ("upcoming-sale", "on-sale", "closed")


def admin_organizers(db: Session) -> list[dict]:
    """Danh sách Ban tổ chức (mới đăng ký trước) kèm số sự kiện, đang bán, chờ duyệt, doanh thu, phí sàn
    (phí theo từng sự kiện). Tóm tắt sự kiện tính một lượt cho mọi BTC (không lặp truy vấn theo BTC)."""
    rows = db.execute(select(Organizer, User.email).join(User, User.id == Organizer.user_id)
                      .order_by(Organizer.created_at.desc(), Organizer.user_id.desc())).all()
    events = db.scalars(select(Event).where(Event.organizer_id.is_not(None))).all()
    by_org: dict[int, list[dict]] = {}
    for ev, s in zip(events, event_summaries(db, list(events))):
        by_org.setdefault(ev.organizer_id, []).append(s)
    from app.services import withdrawals  # import muộn: withdrawals import manage

    bal = withdrawals.balances(db, [o.user_id for o, _ in rows])  # một lượt cho mọi BTC
    out = []
    for o, email in rows:
        evs = by_org.get(o.user_id, [])
        b = bal[o.user_id]
        out.append({"userId": o.user_id, "code": f"ORG-{o.user_id:05d}", "orgName": o.org_name, "email": email,
                    "phone": o.phone, "createdAt": iso_vn(o.created_at), "events": len(evs),
                    "live": sum(e["phase"] in LIVE_PHASES for e in evs),
                    "pending": sum(e["phase"] == "pending" for e in evs),
                    "revenue": sum(e["revenue"] for e in evs), "fee": sum(fee_of(e["revenue"]) for e in evs),
                    "available": b["available"], "held": b["held"], "pendingWithdrawals": b["pending"]})
    return out


def admin_organizer_events(db: Session, organizer_id: int) -> list[dict]:
    if db.get(Organizer, organizer_id) is None:
        raise HTTPException(404, ORGANIZER_NOT_FOUND)
    first_start = (select(func.min(Show.starts_at)).where(Show.event_id == Event.id).correlate(Event).scalar_subquery())
    events = db.scalars(select(Event).where(Event.organizer_id == organizer_id).order_by(first_start, Event.id)).all()
    return event_summaries(db, list(events))


def review(db: Session, event_id: int, decision: Any, reason: Any) -> dict:
    """Duyệt / trả lại hồ sơ — MỘT câu UPDATE có điều kiện status = 'pending':
    hai quản trị viên bấm cùng lúc thì chỉ một người thành công, người kia nhận 409."""
    decision = as_str(decision)
    if decision not in ("approve", "reject"):
        raise HTTPException(400, "Quyết định không hợp lệ")
    status = "approved" if decision == "approve" else "rejected"
    note = (as_str(reason).strip()[:300] or DEFAULT_REJECT_REASON) if status == "rejected" else None
    if status == "approved":
        first = db.scalar(select(func.min(Show.starts_at)).where(Show.event_id == event_id))
        pending = db.scalar(select(exists().where(Event.id == event_id, Event.organizer_id.is_not(None),
                                                  Event.status == "pending")))
        if pending and first is not None and first <= now_utc():
            raise HTTPException(409, "Đã qua giờ diễn, không thể duyệt")  # duyệt muộn: sự kiện không lên trang chủ
    row = db.execute(
        update(Event)
        .where(Event.id == event_id, Event.organizer_id.is_not(None), Event.status == "pending")
        .values(status=status, reject_reason=note, reviewed_at=func.now())
        .returning(Event.slug, Event.status)
    ).first()
    if row is None:
        is_org_event = db.scalar(select(exists().where(Event.id == event_id, Event.organizer_id.is_not(None))))
        raise HTTPException(409, "Hồ sơ này đã được xử lý") if is_org_event else HTTPException(404, REVIEW_NOT_FOUND)
    return {"ok": True, "slug": row.slug, "status": row.status}


# ---------------------------------------------------------------- dashboard (giai đoạn 7)
FEE_RATE = 5  # % phí sàn trên doanh thu (tiền khách trả — Ban tổ chức chịu giảm giá)
WEEKDAY_CODE = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
EVENT_NOT_FOUND = "Sự kiện không tồn tại"


def fee_of(revenue: int) -> int:
    """Phí sàn của MỘT sự kiện, làm tròn tới đồng — cộng phí từng sự kiện, không tính trên tổng"""
    return (revenue * FEE_RATE + 50) // 100


def sale_opens_at(e: Event) -> datetime | None:
    """Giờ mở bán: sale_start nếu Ban tổ chức đặt, không thì lúc sàn duyệt"""
    return e.sale_start or e.reviewed_at


def phase_of(e: Event, last_show_start: datetime | None, now: datetime) -> str:
    """pending | rejected | cancelled | upcoming-sale | on-sale | closed | ended.
    closed = suất cuối đã bắt đầu nhưng chưa sang ngày (giờ VN) hôm sau; ended = đã qua ngày của suất cuối."""
    if e.status != "approved":
        return e.status
    if last_show_start is not None and last_show_start.astimezone(VN).date() < now.astimezone(VN).date():
        return "ended"
    if last_show_start is not None and last_show_start <= now:
        return "closed"
    opens = sale_opens_at(e)
    if opens is not None and opens > now:
        return "upcoming-sale"
    return "on-sale"


def parse_sale_start(raw: Any, show_start: datetime) -> datetime | None:
    """"YYYY-MM-DDTHH:mm" giờ VN; rỗng → None (mở bán khi được duyệt)"""
    s = as_str(raw).strip()
    if not s:
        return None
    try:
        value = datetime.strptime(s, "%Y-%m-%dT%H:%M").replace(tzinfo=VN) if SALE_RE.match(s) else None
    except ValueError:
        value = None
    if value is None:
        raise HTTPException(400, "Giờ mở bán không hợp lệ")
    if value >= show_start:
        raise HTTPException(400, "Giờ mở bán phải trước giờ diễn")
    return value


SALE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")


def organizer_stats(db: Session, organizer_id: int, days: int) -> list[dict]:
    """Doanh thu (tiền khách trả) + số vé theo NGÀY giờ VN, đủ `days` ngày kết thúc hôm nay (dùng VIEW v_daily_revenue)"""
    today = now_utc().astimezone(VN).date()
    first = today - timedelta(days=days - 1)
    rows = db.execute(
        text("SELECT day, revenue, tickets FROM v_daily_revenue WHERE organizer_id = :uid AND day BETWEEN :d0 AND :d1"),
        {"uid": organizer_id, "d0": first, "d1": today},
    ).all()
    by_day = {r.day: r for r in rows}
    out = []
    for i in range(days):
        d = first + timedelta(days=i)
        r = by_day.get(d)
        out.append({"date": d.isoformat(), "label": WEEKDAY_CODE[d.weekday()],
                    "revenue": int(r.revenue) if r else 0, "tickets": int(r.tickets) if r else 0})
    return out


EDIT_MODE = {"pending": "full", "rejected": "full", "upcoming-sale": "limited", "on-sale": "limited"}


def editable_of(ev: Event, phase: str) -> dict:
    """full: sửa mọi thứ (chưa duyệt) · limited: đã duyệt, chưa diễn · none: đang diễn / đã diễn / đã huỷ"""
    mode = EDIT_MODE.get(phase, "none")
    return {"mode": mode, "saleStart": mode == "full" or phase == "upcoming-sale"}


def event_form(db: Session, ev: Event, show: Show | None) -> dict:
    """Giá trị hiện tại cho form sửa; tiers[*].sold = bán sẵn + đã bán (kho chung, đúng cả sự kiện bán theo ghế)"""
    stats = tier_stats(db, [ev])
    tiers = db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.active)
                       .order_by(TicketTier.sort_order, TicketTier.id)).all()
    prices = None
    if ev.layout != "list":
        prices = {t.group_id or t.id: t.price for t in tiers}
    return {
        "title": ev.title, "category": ev.category_id, "city": ev.city, "venue": ev.venue, "address": ev.address,
        "date": show.starts_at.astimezone(VN).date().isoformat() if show else None,
        "startTime": hhmm(show.starts_at) if show else None, "endTime": hhmm(show.end_time) if show else None,
        "description": "\n\n".join(ev.description or []),
        "saleStart": ev.sale_start.astimezone(VN).strftime("%Y-%m-%dT%H:%M") if ev.sale_start else "",
        "layout": ev.layout, "mapId": ev.map_id, "prices": prices,
        "tiers": [{"id": t.id, "name": t.name, "price": t.price, "quantity": t.capacity, "perks": t.perks,
                   "sold": (lambda st: st.presold + st.sold if st else 0)(stats.get((ev.id, t.id)))} for t in tiers],
    }


def organizer_event_detail(db: Session, organizer_id: int, event_id: int) -> dict:
    """Ngăn kéo sự kiện: bán theo hạng vé, tiền (gộp − giảm giá = doanh thu; phí 5%; thực nhận), mốc thời gian, 5 đơn mới"""
    ev = db.scalar(select(Event).where(Event.id == event_id, Event.organizer_id == organizer_id))
    if ev is None:
        raise HTTPException(404, EVENT_NOT_FOUND)
    paid = (Order.status == "paid", Order.event_id == ev.id)
    per_tier = {tid: (int(q), int(r)) for tid, q, r in db.execute(
        select(OrderItem.tier_id, func.sum(OrderItem.qty), func.sum(OrderItem.price * OrderItem.qty))
        .join(Order, Order.id == OrderItem.order_id).where(*paid).group_by(OrderItem.tier_id))}
    tiers = [{"id": t.id, "name": t.name, "price": t.price, "capacity": t.capacity,
              "sold": per_tier.get(t.id, (0, 0))[0], "revenue": per_tier.get(t.id, (0, 0))[1]}
             for t in db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id)
                                 .order_by(TicketTier.sort_order, TicketTier.id))]
    discount, revenue, orders = db.execute(
        select(func.coalesce(func.sum(Order.discount), 0), func.coalesce(func.sum(Order.total), 0), func.count())
        .where(*paid)).one()
    revenue = int(revenue)
    fee = fee_of(revenue)
    first_show = db.scalars(select(Show).where(Show.event_id == ev.id).order_by(Show.starts_at, Show.id)).first()
    last_start = db.scalar(select(func.max(Show.starts_at)).where(Show.event_id == ev.id))
    return {
        "form": event_form(db, ev, first_show),
        "editable": editable_of(ev, phase_of(ev, last_start, now_utc())),
        "tiers": tiers,
        "money": {"gross": sum(t["revenue"] for t in tiers), "discount": int(discount), "revenue": revenue,
                  "fee": fee, "net": revenue - fee, "orders": int(orders)},
        "timeline": {"createdAt": iso_vn(ev.created_at), "reviewedAt": iso_vn(ev.reviewed_at),
                     "saleOpensAt": iso_vn(sale_opens_at(ev)),
                     "startsAt": iso_vn(first_show.starts_at) if first_show else None},
        "recentOrders": _recent_orders(db, organizer_id, limit=5, event_id=ev.id),
    }


STALE_DAYS_MSG = "Số ngày không hợp lệ"


def stale_events(db: Session, days_raw: Any) -> dict:
    """Sự kiện đang bán mà không có đơn đã thanh toán trong `days` ngày (Q7 events_without_sales.sql: NOT EXISTS)"""
    from app.services import sql_queries  # import muộn: tránh vòng import khi nạp app.services

    raw = as_str(days_raw).strip()
    if not re.fullmatch(r"[0-9]{1,2}", raw) or not 1 <= int(raw) <= 90:
        raise HTTPException(400, STALE_DAYS_MSG)
    days = int(raw)
    rows = sql_queries.run(db, "events_without_sales", days=days, now=now_utc())
    return {"days": days, "events": [{
        "id": r["id"], "slug": r["slug"], "title": r["title"], "organizerId": r["organizer_id"], "orgName": r["org_name"],
        "saleOpensAt": iso_vn(r["sale_opens_at"]), "startsAt": iso_vn(r["last_start"]), "lastSaleAt": iso_vn(r["last_sale_at"]),
    } for r in rows]}


def admin_event_preview(db: Session, event_id: int) -> dict:
    """Admin xem trước MỌI sự kiện (kể cả chờ duyệt / bị trả lại / đã huỷ) bằng đúng JSON trang khán giả"""
    from app.services.catalog import build_event_detail  # import muộn: catalog không phụ thuộc manage

    ev = db.get(Event, event_id)
    if ev is None:
        raise HTTPException(404, EVENT_NOT_FOUND)
    org = None
    if ev.organizer_id is not None:
        o, email = db.execute(select(Organizer, User.email).join(User, User.id == Organizer.user_id)
                              .where(Organizer.user_id == ev.organizer_id)).one()
        org = {"orgName": o.org_name, "code": f"ORG-{o.user_id:05d}", "email": email, "phone": o.phone}
    detail = build_event_detail(db, ev, with_related=False)
    return {"event": detail.model_dump(by_alias=True, mode="json"), "summary": event_summaries(db, [ev])[0],
            "organizer": org}
