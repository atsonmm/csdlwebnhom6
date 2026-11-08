"""Một nguồn số liệu kho cho cả khán giả, Ban tổ chức và Admin: sức chứa / bán sẵn / đã bán / còn lại theo hạng vé.

- Bán theo loại vé hoặc theo khu: bảng tier_stock (thiếu dòng → sức chứa của hạng, chưa bán vé nào).
- Bán theo ghế: sức chứa = số ghế của nhóm trong sơ đồ; bán sẵn = seat_holds không có đơn; đã bán = seat_holds có đơn.
Chỉ tính hạng vé và suất diễn đang active."""
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Event, MapSeat, Show, TicketTier
from app.models.sales import SeatHold, TierStock


@dataclass(frozen=True)
class TierStat:
    capacity: int
    presold: int
    sold: int
    remaining: int


def _stat(capacity: int, presold: int, sold: int) -> TierStat:
    return TierStat(capacity, presold, sold, max(0, capacity - presold - sold))


def show_stats(db: Session, events: list[Event], show_id: str | None = None) -> dict[tuple[int, str, str], TierStat]:
    """Số liệu theo (event_id, show_id, tier_id) cho mọi suất active (hoặc chỉ suất show_id)"""
    if not events:
        return {}
    by_id = {e.id: e for e in events}
    show_q = select(Show.event_id, Show.id).where(Show.event_id.in_(by_id), Show.active)
    if show_id is not None:
        show_q = show_q.where(Show.id == show_id)
    shows: dict[int, list[str]] = defaultdict(list)
    for eid, sid in db.execute(show_q):
        shows[eid].append(sid)
    tiers = db.execute(select(TicketTier.event_id, TicketTier.id, TicketTier.group_id, TicketTier.capacity)
                       .where(TicketTier.event_id.in_(by_id), TicketTier.active)).all()

    seat_ids = [eid for eid, e in by_id.items() if e.layout == "seats"]
    stock_ids = [eid for eid in by_id if eid not in seat_ids]
    out: dict[tuple[int, str, str], TierStat] = {}

    if stock_ids:
        rows = {(s.event_id, s.show_id, s.tier_id): s for s in db.scalars(
            select(TierStock).join(Show, (Show.event_id == TierStock.event_id) & (Show.id == TierStock.show_id))
            .where(TierStock.event_id.in_(stock_ids), Show.active,
                   *([TierStock.show_id == show_id] if show_id is not None else [])))}
        for eid, tid, _group, cap in tiers:
            if eid not in stock_ids:
                continue
            for sid in shows.get(eid, []):
                s = rows.get((eid, sid, tid))
                out[(eid, sid, tid)] = _stat(s.capacity, s.presold, s.sold) if s else _stat(cap, 0, 0)

    if seat_ids:
        map_ids = {by_id[eid].map_id for eid in seat_ids}
        seat_count = {(m, g): int(n) for m, g, n in db.execute(
            select(MapSeat.map_id, MapSeat.group_id, func.count()).where(MapSeat.map_id.in_(map_ids))
            .group_by(MapSeat.map_id, MapSeat.group_id))}
        held: dict[tuple[int, str, str], list[int]] = defaultdict(lambda: [0, 0])  # (eid, sid, group) → [bán sẵn, đã bán]
        for eid, sid, group, has_order, n in db.execute(
            select(SeatHold.event_id, SeatHold.show_id, MapSeat.group_id, SeatHold.order_id.is_not(None), func.count())
            .join(Event, Event.id == SeatHold.event_id)
            .join(MapSeat, (MapSeat.map_id == Event.map_id) & (MapSeat.id == SeatHold.seat_id))
            .join(Show, (Show.event_id == SeatHold.event_id) & (Show.id == SeatHold.show_id))
            .where(SeatHold.event_id.in_(seat_ids), Show.active,
                   *([SeatHold.show_id == show_id] if show_id is not None else []))
            .group_by(SeatHold.event_id, SeatHold.show_id, MapSeat.group_id, SeatHold.order_id.is_not(None))
        ):
            held[(eid, sid, group)][1 if has_order else 0] += int(n)
        for eid, tid, group, _cap in tiers:
            if eid not in seat_ids:
                continue
            g = group or tid
            cap = seat_count.get((by_id[eid].map_id, g), 0)
            for sid in shows.get(eid, []):
                presold, sold = held.get((eid, sid, g), (0, 0))
                out[(eid, sid, tid)] = _stat(cap, presold, sold)
    return out


def tier_stats(db: Session, events: list[Event], show_id: str | None = None) -> dict[tuple[int, str], TierStat]:
    """Số liệu theo (event_id, tier_id); show_id=None → cộng mọi suất active"""
    acc: dict[tuple[int, str], list[int]] = {}
    for (eid, _sid, tid), st in show_stats(db, events, show_id).items():
        a = acc.setdefault((eid, tid), [0, 0, 0, 0])
        a[0] += st.capacity
        a[1] += st.presold
        a[2] += st.sold
        a[3] += st.remaining
    # Tổng "còn lại" = cộng còn lại từng suất (không tính lại từ tổng, tránh lệch khi một suất bán vượt)
    return {k: TierStat(*a) for k, a in acc.items()}
