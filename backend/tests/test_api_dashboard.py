"""Giai đoạn 7 — dashboard Ban tổ chức: saleStart, phase, /organizer/stats, /organizer/events/{id}"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, Show
from app.models.sales import Order
from app.utils.timefmt import VN
from tests.api_helpers import drop_org_event, make_org_event, org_show_id
from tests.booking_helpers import insert_order, make_customer

EVENTS = "/api/organizer/events"
DAY = (datetime.now(VN) + timedelta(days=30)).date()
SHOW = f"{DAY.strftime('%Y%m%d')}-1930"
OK = {
    "title": "Đêm Nhạc Dashboard", "category": "nhac-song", "city": "Hà Nội", "venue": "Nhà hát Lớn", "address": "",
    "date": DAY.isoformat(), "startTime": "19:30", "endTime": "22:00",
    "description": "Sự kiện thử cho dashboard Ban tổ chức.",
    "tiers": [{"name": "Vé thường", "price": 300000, "quantity": 100}, {"name": "VIP", "price": 900000, "quantity": 20}],
}


@pytest.fixture(autouse=True)
def drop_created(api_db):
    yield
    api_db.rollback()
    for ev in api_db.scalars(select(Event).where(Event.slug.like("dem-nhac-dashboard%"))):
        drop_org_event(api_db, ev)


def approve(db, event_id: int, when: datetime | None = None) -> None:
    db.execute(update(Event).where(Event.id == event_id)
               .values(status="approved", reviewed_at=when or datetime.now(timezone.utc)))
    db.commit()


def create(c, **over) -> dict:
    r = c.post(EVENTS, json=OK | over)
    assert r.status_code == 201, r.text
    return r.json()["event"]


def vn_at(day, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=VN) + timedelta(hours=hour, minutes=minute)


# ------------------------------------------------------------------ saleStart
def test_sale_start_saved(c, logged_organizer, api_db):
    opens = DAY - timedelta(days=5)
    s = create(c, saleStart=f"{opens.isoformat()}T10:00")
    api_db.expire_all()
    ev = api_db.get(Event, s["id"])
    assert ev.sale_start.astimezone(VN).strftime("%Y-%m-%d %H:%M") == f"{opens.isoformat()} 10:00"
    assert s["saleOpensAt"] == f"{opens.isoformat()}T10:00:00+07:00"


@pytest.mark.parametrize("value,msg", [
    ("ngày mai", "Giờ mở bán không hợp lệ"),
    ("2026-13-01T10:00", "Giờ mở bán không hợp lệ"),
    (f"{DAY.isoformat()}T19:30", "Giờ mở bán phải trước giờ diễn"),
    (f"{(DAY + timedelta(days=1)).isoformat()}T08:00", "Giờ mở bán phải trước giờ diễn"),
])
def test_sale_start_validation(c, logged_organizer, value, msg):
    r = c.post(EVENTS, json=OK | {"saleStart": value})
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_empty_sale_start_means_open_when_approved(c, logged_organizer, api_db):
    s = create(c, saleStart="")
    approve(api_db, s["id"], datetime.now(timezone.utc) - timedelta(hours=1))
    me = next(e for e in c.get("/api/organizer/me").json()["events"] if e["id"] == s["id"])
    assert me["phase"] == "on-sale" and me["saleOpensAt"] == me["reviewedAt"] and me["reviewedAt"] is not None


# ------------------------------------------------------------------ phase
def test_phases(c, logged_organizer, api_db):
    pending = create(c)
    upcoming = create(c, saleStart=f"{(DAY - timedelta(days=2)).isoformat()}T09:00")
    approve(api_db, upcoming["id"])
    rejected = create(c)
    api_db.execute(update(Event).where(Event.id == rejected["id"]).values(status="rejected", reject_reason="Thiếu ảnh"))
    ended = create(c)
    approve(api_db, ended["id"])
    api_db.execute(update(Show).where(Show.event_id == ended["id"])
                   .values(starts_at=datetime.now(timezone.utc) - timedelta(days=2)))
    api_db.commit()
    phase = {e["id"]: e["phase"] for e in c.get("/api/organizer/me").json()["events"]}
    assert phase[pending["id"]] == "pending"
    assert phase[upcoming["id"]] == "upcoming-sale"
    assert phase[rejected["id"]] == "rejected"
    assert phase[ended["id"]] == "ended"


def test_upcoming_sale_event_is_coming_publicly_and_not_bookable(c, logged_organizer, api_db):
    s = create(c, saleStart=f"{(DAY - timedelta(days=2)).isoformat()}T09:00")
    approve(api_db, s["id"])
    assert c.get(f"/api/events/{s['slug']}").json()["status"] == "coming"
    r = c.post("/api/orders", json={"slug": s["slug"], "items": [{"tierId": "ve-1", "qty": 1}], "method": "qr",
                                    "buyer": {"name": "Khách A", "email": "a@x.vn", "phone": "0912345678"}})
    assert r.status_code == 400 and r.json() == {"error": "Sự kiện chưa mở bán"}


# ------------------------------------------------------------------ stats
def test_stats_7_days_vn_days_discount_and_only_own_events(c, logged_organizer, api_db, auth_db):
    s = create(c)
    approve(api_db, s["id"])
    buyer = make_customer(api_db, "mua-dash@x.vn")
    today = datetime.now(VN).date()
    yesterday = today - timedelta(days=1)
    o1 = insert_order(api_db, buyer, s["slug"], SHOW, [("ve-1", 2)], created_at=vn_at(yesterday, 23, 30))
    o2 = insert_order(api_db, buyer, s["slug"], SHOW, [("ve-2", 1)], created_at=vn_at(today, 0, 5))
    api_db.execute(update(Order).where(Order.id == o2.id).values(discount=50000, total=o2.subtotal - 50000))
    api_db.commit()
    other = make_org_event(api_db, slug="btc-khac-dashboard", status="approved")
    insert_order(api_db, buyer, "btc-khac-dashboard", org_show_id(other), [("ve-1", 4)], created_at=vn_at(yesterday, 12))
    try:
        days = c.get("/api/organizer/stats").json()["days"]
        assert len(days) == 7 and days[-1]["date"] == today.isoformat()
        assert [d["date"] for d in days] == sorted(d["date"] for d in days)
        by = {d["date"]: d for d in days}
        assert by[yesterday.isoformat()]["revenue"] == o1.total and by[yesterday.isoformat()]["tickets"] == 2
        assert by[today.isoformat()]["revenue"] == o2.subtotal - 50000 and by[today.isoformat()]["tickets"] == 1
        assert sum(d["revenue"] for d in days) == o1.total + o2.subtotal - 50000
        assert {d["label"] for d in days} <= {"T2", "T3", "T4", "T5", "T6", "T7", "CN"}
    finally:
        drop_org_event(api_db, other)


def test_stats_empty_days_are_zero(c, logged_organizer):
    days = c.get("/api/organizer/stats?days=3").json()["days"]
    assert len(days) == 3 and all(d["revenue"] == 0 and d["tickets"] == 0 for d in days)


@pytest.mark.parametrize("q", ["?days=0", "?days=32", "?days=abc"])
def test_stats_bad_days_400(c, logged_organizer, q):
    assert c.get(f"/api/organizer/stats{q}").status_code == 400


def test_stats_requires_organizer(c, logged_customer):
    assert c.get("/api/organizer/stats").status_code == 403


# ------------------------------------------------------------------ chi tiết (ngăn kéo)
def test_event_detail_money_tiers_timeline(c, logged_organizer, api_db, auth_db):
    s = create(c, saleStart=f"{(DAY - timedelta(days=10)).isoformat()}T10:00")
    approve(api_db, s["id"])
    buyer = make_customer(api_db, "mua-chitiet@x.vn")
    o1 = insert_order(api_db, buyer, s["slug"], SHOW, [("ve-1", 2), ("ve-2", 1)])
    api_db.execute(update(Order).where(Order.id == o1.id).values(discount=50000, total=o1.subtotal - 50000))
    insert_order(api_db, buyer, s["slug"], SHOW, [("ve-1", 1)])
    refunded = insert_order(api_db, buyer, s["slug"], SHOW, [("ve-2", 3)])
    api_db.execute(update(Order).where(Order.id == refunded.id).values(status="refunded"))
    api_db.commit()
    d = c.get(f"/api/organizer/events/{s['id']}").json()
    assert d["tiers"] == [
        {"id": "ve-1", "name": "Vé thường", "price": 300000, "capacity": 100, "sold": 3, "revenue": 900000},
        {"id": "ve-2", "name": "VIP", "price": 900000, "capacity": 20, "sold": 1, "revenue": 900000},
    ]
    m = d["money"]
    assert m["gross"] == 1_800_000 and m["discount"] == 50000 and m["revenue"] == 1_750_000
    assert m["gross"] - m["discount"] == m["revenue"]
    assert m["fee"] == 87500 and m["net"] == 1_750_000 - 87500 and m["orders"] == 2
    t = d["timeline"]
    assert all(t[k] for k in ("createdAt", "reviewedAt", "saleOpensAt", "startsAt"))
    assert t["startsAt"] == f"{DAY.isoformat()}T19:30:00+07:00"
    # đơn đã hoàn tiền KHÔNG được hiện như tiền vào (khớp money.orders = 2)
    assert len(d["recentOrders"]) == 2 and set(d["recentOrders"][0]) == {"id", "total", "created_at", "name", "items"}
    assert refunded.id not in {o["id"] for o in d["recentOrders"]}
    me = c.get("/api/organizer/me").json()
    assert refunded.id not in {o["id"] for o in me["recentOrders"]}


def test_event_detail_of_another_organizer_is_404(c, logged_organizer, api_db):
    other = make_org_event(api_db, slug="btc-khac-chitiet", status="approved")
    try:
        r = c.get(f"/api/organizer/events/{other.id}")
        assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}
        assert c.get("/api/organizer/events/abc").status_code == 404
        assert c.get("/api/organizer/events/99999999999").status_code == 404
    finally:
        drop_org_event(api_db, other)


def test_event_detail_requires_organizer(c, logged_customer):
    assert c.get("/api/organizer/events/1").status_code == 403
