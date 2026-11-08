"""Truy vấn danh mục từ PostgreSQL. Chỉ trả dữ liệu công khai:
sự kiện đã duyệt và active, suất và hạng vé active."""
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session

from app.models.catalog import Category as CategoryRow
from app.models.catalog import HOME_SECTIONS, Event, HomeSlot, MapGroup, MapSeat, MapZone, Show, TicketTier, VenueMap
from app.models.sales import Coupon, SeatHold
from app.models.users import Organizer
from app.config.rules import MAX_PER_ORDER
from app.services.stock import show_stats, tier_stats
from app.schemas.catalog import Availability, Category, CouponOut, EventCard, HomeCard, EventDetail, OrganizerOut, ShowOut, TierOut, TierRemaining
from app.utils.textnorm import normalize_vi
from app.utils.timefmt import hhmm, iso_vn

DEFAULT_ORG_BIO = "Ban tổ chức trên TicketNhịp."
RELATED_LIMIT = 4


# ---------------------------------------------------------------- danh mục, mã giảm giá
def list_categories(db: Session) -> list[Category]:
    rows = db.scalars(select(CategoryRow).order_by(CategoryRow.sort_order)).all()
    return [Category(id=r.id, label=r.label, dot=r.dot) for r in rows]


def get_coupon(db: Session, code: str) -> CouponOut | None:
    row = db.scalar(select(Coupon).where(func.upper(Coupon.code) == code.upper(), Coupon.active))
    return None if row is None else CouponOut(code=row.code, amount=row.amount, min_order=row.min_order)


# ---------------------------------------------------------------- sự kiện công khai
def public_events_query() -> Select:
    """Sự kiện khách xem được: đã duyệt, active, còn ít nhất 1 suất active"""
    has_show = exists().where(Show.event_id == Event.id, Show.active)
    return select(Event).where(Event.status == "approved", Event.active, has_show)


def _active_shows(db: Session, event_ids: list[int]) -> dict[int, list[Show]]:
    out: dict[int, list[Show]] = {i: [] for i in event_ids}
    rows = db.scalars(select(Show).where(Show.event_id.in_(event_ids), Show.active).order_by(Show.starts_at, Show.id))
    for s in rows:
        out[s.event_id].append(s)
    return out


def _sale_status(ev: Event, now: datetime) -> str:
    return "coming" if ev.sale_start is not None and ev.sale_start > now else "on-sale"


def _cards(db: Session, events: list[Event]) -> list[EventCard]:
    """Dựng thẻ cho nhiều sự kiện bằng 3 truy vấn (không truy vấn lặp theo từng sự kiện)"""
    if not events:
        return []
    ids = [e.id for e in events]
    labels = dict(db.execute(select(CategoryRow.id, CategoryRow.label)).all())
    shows = _active_shows(db, ids)
    min_price = dict(
        db.execute(
            select(TicketTier.event_id, func.min(TicketTier.price))
            .where(TicketTier.event_id.in_(ids), TicketTier.active)
            .group_by(TicketTier.event_id)
        ).all()
    )
    now = datetime.now(timezone.utc)
    cards = []
    for e in events:
        first = shows[e.id][0]
        cards.append(
            EventCard(
                slug=e.slug,
                title=e.title,
                category=e.category_id,
                category_label=labels.get(e.category_id, "Khác"),
                city=e.city,
                venue=e.venue,
                start=iso_vn(first.starts_at),
                start_time=hhmm(first.starts_at),
                min_price=min_price.get(e.id, 0),
                status=_sale_status(e, now),
                sale_opens_at=iso_vn(e.sale_start),
                resale_count=e.resale_count,
            )
        )
    return cards


def to_card(db: Session, event: Event) -> EventCard:
    return _cards(db, [event])[0]


def tier_remaining(db: Session, event: Event, show_id: str) -> dict[str, int]:
    """Vé còn lại theo hạng của một suất.
    Theo loại vé hoặc theo khu: capacity trừ presold trừ sold (bảng tier_stock).
    Theo ghế: số ghế của nhóm chưa có trong seat_holds của suất."""
    return {tid: st.remaining for (_eid, tid), st in tier_stats(db, [event], show_id).items()}


def _organizer(db: Session, ev: Event) -> OrganizerOut:
    if ev.organizer_id is not None:
        org = db.get(Organizer, ev.organizer_id)
        return OrganizerOut(name=org.org_name, bio=org.description or DEFAULT_ORG_BIO)
    return OrganizerOut(name=ev.host_name or "[BAN TỔ CHỨC]", bio=ev.host_bio or DEFAULT_ORG_BIO)


def _related(db: Session, ev: Event, limit: int = RELATED_LIMIT) -> list[EventCard]:
    others = db.scalars(public_events_query().where(Event.id != ev.id)).all()
    cards = _cards(db, list(others))
    score = {c.slug: 2 * (c.category == ev.category_id) + (c.city == ev.city) for c in cards}
    cards.sort(key=lambda c: (-score[c.slug], c.start))
    return cards[:limit]


def get_event_detail(db: Session, slug: str) -> EventDetail | None:
    ev = db.scalar(public_events_query().where(Event.slug == slug))
    if ev is None:
        return None
    return build_event_detail(db, ev)


def build_event_detail(db: Session, ev: Event, *, with_related: bool = True) -> EventDetail:
    """JSON trang sự kiện cho MỘT sự kiện bất kỳ trạng thái (bản công khai lọc trước bằng public_events_query;
    Admin xem trước hồ sơ chờ duyệt dùng with_related=False)"""
    card = to_card(db, ev)
    shows = _active_shows(db, [ev.id])[ev.id]
    category = db.get(CategoryRow, ev.category_id)
    rows = db.execute(
        select(TicketTier, MapGroup.label, MapGroup.color)
        .outerjoin(MapGroup, (MapGroup.map_id == ev.map_id) & (MapGroup.id == TicketTier.group_id))
        .where(TicketTier.event_id == ev.id, TicketTier.active)
        .order_by(TicketTier.sort_order, TicketTier.id)
    ).all()
    now = datetime.now(timezone.utc)
    open_ids = [s.id for s in shows if s.starts_at > now]
    per_show = show_stats(db, [ev])
    current = open_ids[0] if open_ids else shows[0].id  # vé hiển thị theo suất còn mở đầu tiên
    remaining = {tid: st.remaining for (_e, sid, tid), st in per_show.items() if sid == current}
    sold_out = not any(st.remaining > 0 for (_e, sid, _t), st in per_show.items() if sid in open_ids)
    tiers = [
        TierOut(
            id=t.id,
            name=t.name,
            price=t.price,
            perks=t.perks,
            capacity=t.capacity,
            remaining=remaining.get(t.id, 0),
            max=t.max_per_order,
            group=t.group_id,
            group_label=label if t.group_id else None,
            color=color if t.group_id else None,
        )
        for t, label, color in rows
    ]
    return EventDetail(
        **card.model_dump(),
        marker=category.dot if category else "bg-ink",
        address=ev.address,
        end_time=hhmm(shows[0].end_time),
        shows=[
            ShowOut(id=s.id, start=iso_vn(s.starts_at), start_time=hhmm(s.starts_at), end_time=hhmm(s.end_time),
                    closed=s.starts_at <= now)
            for s in shows
        ],
        layout=ev.layout,
        map=ev.map_id,
        organizer=_organizer(db, ev),
        description=list(ev.description),
        notes=list(ev.notes),
        tiers=tiers,
        max_per_order=MAX_PER_ORDER,
        sold_out=sold_out,
        related=_related(db, ev) if with_related else [],
    )


class EventNotFound(Exception):
    pass


class ShowNotFound(Exception):
    pass


def availability(db: Session, slug: str, show_id: str | None) -> Availability:
    """Vé còn lại theo hạng của một suất (mặc định: suất active sớm nhất).
    Ném EventNotFound / ShowNotFound nếu sự kiện hoặc suất không công khai."""
    ev = db.scalar(public_events_query().where(Event.slug == slug))
    if ev is None:
        raise EventNotFound
    shows = _active_shows(db, [ev.id])[ev.id]
    show = next((s for s in shows if s.id == show_id), None) if show_id else shows[0]
    if show is None:
        raise ShowNotFound
    remaining = tier_remaining(db, ev, show.id)
    order = db.scalars(select(TicketTier.id).where(TicketTier.event_id == ev.id, TicketTier.active)
                       .order_by(TicketTier.sort_order, TicketTier.id)).all()
    unavailable = None
    if ev.layout == "seats":
        unavailable = sorted(db.scalars(select(SeatHold.seat_id).where(SeatHold.event_id == ev.id,
                                                                        SeatHold.show_id == show.id)))
    return Availability(show=show.id, tiers=[TierRemaining(id=t, remaining=remaining[t]) for t in order],
                        unavailable_seats=unavailable)


def _escape_like(word: str) -> str:
    r"""Ký tự % _ \ người dùng gõ vào là chữ thường, không phải ký tự đại diện của LIKE"""
    return word.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def list_events(db: Session, *, q: str | None = None, category: str | None = None, city: str | None = None,
                organizer: bool = False, sort: Literal["start", "reviewed"] = "start", limit: int = 60) -> list[EventCard]:
    """Danh sách sự kiện công khai. q: tìm không dấu, mọi từ phải xuất hiện trong search_text."""
    stmt = public_events_query()
    for word in normalize_vi(q or "").split():
        stmt = stmt.where(Event.search_text.ilike(f"%{_escape_like(word)}%", escape="\\"))
    if category:
        stmt = stmt.where(Event.category_id == category)
    if city:
        stmt = stmt.where(Event.city == city)
    if organizer:
        stmt = stmt.where(Event.organizer_id.is_not(None))
    if sort == "reviewed":
        stmt = stmt.order_by(Event.reviewed_at.desc().nulls_last(), Event.id.desc())
    else:
        first_start = (select(func.min(Show.starts_at)).where(Show.event_id == Event.id, Show.active)
                       .correlate(Event).scalar_subquery())
        stmt = stmt.order_by(first_start, Event.id)
    return _cards(db, list(db.scalars(stmt.limit(limit))))


# ---------------------------------------------------------------- trang chủ
def home_sections(db: Session) -> dict[str, list[HomeCard]]:
    """Đủ 9 khu trang chủ, mỗi khu theo thứ tự position; bỏ slot có sự kiện không công khai"""
    public = public_events_query().subquery()
    rows = db.execute(
        select(HomeSlot, Event)
        .join(Event, Event.id == HomeSlot.event_id)
        .where(HomeSlot.event_id.in_(select(public.c.id)))
        .order_by(HomeSlot.section, HomeSlot.position)
    ).all()
    events = {e.id: e for _, e in rows}
    cards = {c.slug: c for c in _cards(db, list(events.values()))}
    out: dict[str, list[HomeCard]] = {name: [] for name in HOME_SECTIONS}
    for slot, ev in rows:
        out[slot.section].append(HomeCard(**cards[ev.slug].model_dump(), meta=slot.meta or {}))
    return out


# ---------------------------------------------------------------- sơ đồ địa điểm
def get_map(db: Session, map_id: str) -> dict | None:
    """Sơ đồ theo đúng dạng object JS cũ (ZONE_MAPS / getSeatMap) để ZoneMap, SeatMap dùng thẳng"""
    vm = db.get(VenueMap, map_id)
    if vm is None:
        return None
    groups = db.scalars(select(MapGroup).where(MapGroup.map_id == map_id).order_by(MapGroup.sort_order, MapGroup.id))
    out: dict = {"id": vm.id, "kind": vm.kind, "name": vm.name}
    if vm.view_box is not None:
        out["viewBox"] = vm.view_box
    out.update(vm.decor or {})
    out["groups"] = {
        g.id: {"label": g.label, "color": g.color, "ink": g.ink, "max": g.max_per_order, "perks": g.perks}
        for g in groups
    }
    if vm.kind == "zones":
        zones = db.scalars(select(MapZone).where(MapZone.map_id == map_id).order_by(MapZone.sort_order, MapZone.id))
        out["zones"] = [
            {"id": z.id, "label": z.label, "group": z.group_id, "cap": z.capacity, "text": z.text, "shape": z.shape}
            for z in zones
        ]
    else:
        seats = db.scalars(select(MapSeat).where(MapSeat.map_id == map_id).order_by(MapSeat.sort_order, MapSeat.id))
        out["seats"] = [
            {"id": s.id, "x": s.x, "y": s.y, "row": s.row_label, "num": s.num, "section": s.section,
             "group": s.group_id, "label": s.label}
            for s in seats
        ]
    return out
