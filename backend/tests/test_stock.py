"""Task S1 — một nguồn số liệu kho (stock.tier_stats), phase 'closed', chi tiết sự kiện closed/soldOut/maxPerOrder,
tổng số của Admin chỉ tính đơn đã thanh toán"""
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import delete, func, select, update

from app.models.catalog import Event, MapSeat, Show, TicketTier
from app.models.sales import Order, SeatHold, Ticket, TierStock
from app.services import manage, stock
from app.utils.timefmt import VN
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer


def _event(db, layout: str, min_shows: int = 1) -> Event:
    n_shows = (select(func.count()).select_from(Show).where(Show.event_id == Event.id, Show.active)
               .correlate(Event).scalar_subquery())
    return db.scalar(select(Event).where(Event.layout == layout, Event.status == "approved", Event.active,
                                         n_shows >= min_shows).order_by(Event.id))


def _first_show(db, ev: Event) -> Show:
    return db.scalars(select(Show).where(Show.event_id == ev.id, Show.active).order_by(Show.starts_at, Show.id)).first()


# ------------------------------------------------------------------ tier_stats
def test_list_and_zones_use_tier_stock_with_presold(api, api_db):
    for layout in ("list", "zones"):
        ev = _event(api_db, layout)
        show = _first_show(api_db, ev)
        stats = stock.tier_stats(api_db, [ev], show.id)
        rows = api_db.scalars(select(TierStock).where(TierStock.event_id == ev.id, TierStock.show_id == show.id)).all()
        assert rows, layout
        for s in rows:
            st = stats[(ev.id, s.tier_id)]
            assert (st.capacity, st.presold, st.sold) == (s.capacity, s.presold, s.sold)
            assert st.remaining == max(0, s.capacity - s.presold - s.sold)


def test_seats_counted_from_seat_holds(api, api_db, auth_db):
    ev = _event(api_db, "seats")
    show = _first_show(api_db, ev)
    tier = api_db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.active)
                          .order_by(TicketTier.sort_order)).first()
    group = tier.group_id or tier.id
    held = select(SeatHold.seat_id).where(SeatHold.event_id == ev.id, SeatHold.show_id == show.id)
    free = api_db.scalars(select(MapSeat.id).where(MapSeat.map_id == ev.map_id, MapSeat.group_id == group,
                                                   MapSeat.id.not_in(held)).order_by(MapSeat.id).limit(2)).all()
    buyer = make_customer(api_db, "ghe-stock@x.vn")
    insert_order(api_db, buyer, ev.slug, show.id, seats=[(tier.id, s) for s in free])
    try:
        st = stock.tier_stats(api_db, [ev], show.id)[(ev.id, tier.id)]
        in_group = (SeatHold.event_id == ev.id, SeatHold.show_id == show.id,
                    SeatHold.seat_id.in_(select(MapSeat.id).where(MapSeat.map_id == ev.map_id, MapSeat.group_id == group)))
        capacity = api_db.scalar(select(func.count()).select_from(MapSeat).where(
            MapSeat.map_id == ev.map_id, MapSeat.group_id == group))
        presold = api_db.scalar(select(func.count()).select_from(SeatHold).where(*in_group, SeatHold.order_id.is_(None)))
        sold = api_db.scalar(select(func.count()).select_from(SeatHold).where(*in_group, SeatHold.order_id.is_not(None)))
        assert sold >= 2
        assert (st.capacity, st.presold, st.sold, st.remaining) == (capacity, presold, sold, capacity - presold - sold)
        assert not api_db.scalars(select(TierStock).where(TierStock.event_id == ev.id)).first()
    finally:
        api_db.rollback()
        api_db.execute(delete(SeatHold).where(SeatHold.event_id == ev.id, SeatHold.order_id.is_not(None)))
        api_db.commit()


def test_missing_stock_row_defaults_to_capacity(api, api_db):
    ev = make_org_event(api_db, slug="stock-thieu-dong")
    try:
        assert api_db.scalars(select(TierStock).where(TierStock.event_id == ev.id)).first() is None
        st = stock.tier_stats(api_db, [ev])[(ev.id, "ve-1")]
        assert (st.capacity, st.presold, st.sold, st.remaining) == (50, 0, 0, 50)
    finally:
        drop_org_event(api_db, ev)


def test_aggregate_over_shows(api, api_db):
    ev = next(e for layout in ("zones", "list") if (e := _event(api_db, layout, min_shows=2)))
    shows = api_db.scalars(select(Show.id).where(Show.event_id == ev.id, Show.active)).all()
    total = stock.tier_stats(api_db, [ev])
    per_show = [stock.tier_stats(api_db, [ev], sid) for sid in shows]
    assert total
    for key, st in total.items():
        assert st.capacity == sum(p[key].capacity for p in per_show)
        assert st.presold == sum(p[key].presold for p in per_show)
        assert st.sold == sum(p[key].sold for p in per_show)
        assert st.remaining == sum(p[key].remaining for p in per_show)


def test_rules_and_fee():
    from app.config import rules

    assert rules.MAX_PER_ORDER == 10 and rules.TIER_MAX_PER_ORDER == 10
    assert manage.fee_of(0) == 0 and manage.fee_of(1_000_000) == 50_000 and manage.fee_of(10) == 1 and manage.fee_of(9) == 0


# ------------------------------------------------------------------ phase closed
def test_phase_closed_after_start_same_day():
    ev = Event(status="approved", sale_start=None, reviewed_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    start = datetime(2026, 11, 20, 19, 30, tzinfo=VN)
    assert manage.phase_of(ev, start, start - timedelta(minutes=1)) == "on-sale"
    assert manage.phase_of(ev, start, start) == "closed"
    assert manage.phase_of(ev, start, datetime(2026, 11, 20, 23, 59, tzinfo=VN)) == "closed"
    assert manage.phase_of(ev, start, datetime(2026, 11, 21, 0, 0, tzinfo=VN)) == "ended"


# ------------------------------------------------------------------ chi tiết sự kiện
def _two_show_event(api_db, slug: str) -> tuple[Event, str, str]:
    """Sự kiện đã duyệt: suất 1 (ngày mai) hết vé, suất 2 (ngày kia) còn vé"""
    ev = make_org_event(api_db, slug=slug, reviewed_at=datetime.now(timezone.utc) - timedelta(days=1),
                        starts_at=datetime.combine(datetime.now(VN).date() + timedelta(days=1), time(19, 30), tzinfo=VN))
    s1 = ev._test_show_id
    day2 = datetime.now(VN).date() + timedelta(days=2)
    s2 = day2.strftime("%Y%m%d") + "-1930"
    api_db.add(Show(event_id=ev.id, id=s2, starts_at=datetime.combine(day2, time(19, 30), tzinfo=VN), end_time=time(22, 0)))
    api_db.flush()
    api_db.add_all([TierStock(event_id=ev.id, show_id=s1, tier_id="ve-1", capacity=50, presold=50, sold=0),
                    TierStock(event_id=ev.id, show_id=s2, tier_id="ve-1", capacity=50, presold=10, sold=0)])
    api_db.commit()
    return ev, s1, s2


def test_detail_closed_show_and_sold_out_across_shows(api, api_db):
    ev, s1, s2 = _two_show_event(api_db, "hai-suat-stock")
    try:
        body = api.get(f"/api/events/{ev.slug}").json()
        assert body["maxPerOrder"] == 10
        assert [(s["id"], s["closed"]) for s in body["shows"]] == [(s1, False), (s2, False)]
        assert body["soldOut"] is False  # suất 1 hết nhưng suất 2 còn
        # suất 1 đã bắt đầu → đóng; vé hiển thị theo suất mở đầu tiên
        api_db.execute(update(Show).where(Show.event_id == ev.id, Show.id == s1)
                       .values(starts_at=datetime.now(timezone.utc) - timedelta(minutes=5)))
        api_db.commit()
        body = api.get(f"/api/events/{ev.slug}").json()
        closed = {s["id"]: s["closed"] for s in body["shows"]}
        assert closed == {s1: True, s2: False}
        assert body["tiers"][0]["remaining"] == 40
        assert body["soldOut"] is False
        # suất mở còn lại cũng hết → hết vé
        api_db.execute(update(TierStock).where(TierStock.event_id == ev.id, TierStock.show_id == s2).values(presold=50))
        api_db.commit()
        assert api.get(f"/api/events/{ev.slug}").json()["soldOut"] is True
    finally:
        drop_org_event(api_db, ev)


def test_detail_no_open_show_is_sold_out(api, api_db):
    ev = make_org_event(api_db, slug="het-suat-mo", reviewed_at=datetime.now(timezone.utc) - timedelta(days=1),
                        starts_at=datetime.now(timezone.utc) - timedelta(minutes=30))
    try:
        body = api.get(f"/api/events/{ev.slug}").json()
        assert body["shows"][0]["closed"] is True and body["soldOut"] is True
    finally:
        drop_org_event(api_db, ev)


# ------------------------------------------------------------------ tóm tắt BTC khớp /availability
def test_summary_sold_matches_availability(api, api_db, auth_db):
    ev = make_org_event(api_db, slug="khop-con-lai", reviewed_at=datetime.now(timezone.utc) - timedelta(days=1))
    try:
        sid = ev._test_show_id
        api_db.add(TierStock(event_id=ev.id, show_id=sid, tier_id="ve-1", capacity=50, presold=7, sold=0))
        api_db.commit()
        buyer = make_customer(api_db, "khop@x.vn")
        insert_order(api_db, buyer, ev.slug, sid, [("ve-1", 3)])
        api_db.execute(update(TierStock).where(TierStock.event_id == ev.id).values(sold=3))
        api_db.commit()
        s = manage.event_summaries(api_db, [ev])[0]
        avail = api.get(f"/api/events/{ev.slug}/availability").json()
        remaining = sum(t["remaining"] for t in avail["tiers"])
        assert s["capacity"] == 50 and s["sold"] == 10
        assert s["sold"] == s["capacity"] - remaining
    finally:
        drop_org_event(api_db, ev)


# ------------------------------------------------------------------ Admin overview
def test_admin_overview_totals_paid_only(c, logged_admin, api_db):
    ev = make_org_event(api_db, slug="admin-tong-paid", reviewed_at=datetime.now(timezone.utc) - timedelta(days=1))
    try:
        buyer = make_customer(api_db, "tong@x.vn")
        insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", 2)])
        refunded = insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", 4)])
        refunded.status = "refunded"
        api_db.commit()
        t = c.get("/api/admin/overview").json()["totals"]
        paid = Order.status == "paid"
        assert t["orders"] == api_db.scalar(select(func.count()).select_from(Order).where(paid))
        assert t["tickets"] == api_db.scalar(select(func.count()).select_from(Ticket)
                                             .join(Order, Order.id == Ticket.order_id).where(paid))
        per_event = api_db.execute(select(Event.organizer_id.is_not(None), func.sum(Order.total))
                                   .join(Event, Event.id == Order.event_id).where(paid).group_by(Event.id)).all()
        org = [int(r) for is_org, r in per_event if is_org]
        platform = sum(int(r) for is_org, r in per_event if not is_org)
        assert t["orgRevenue"] == sum(org) and t["platformRevenue"] == platform
        assert t["revenue"] == sum(org) + platform
        assert t["fee"] == sum(manage.fee_of(r) for r in org)
        assert t["fee"] >= manage.fee_of(2 * 200000)
    finally:
        drop_org_event(api_db, ev)
