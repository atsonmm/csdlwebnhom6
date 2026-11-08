"""POST /api/organizer/events + số liệu bán trên /api/organizer/me"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, Show, TicketTier
from app.models.sales import TierStock
from app.services import manage
from app.utils.timefmt import VN
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer

EVENTS = "/api/organizer/events"
FUTURE = (datetime.now(VN) + timedelta(days=30)).date().isoformat()
OK = {
    "title": "Đêm Nhạc Thử Nghiệm", "category": "nhac-song", "city": "Hà Nội", "venue": "Nhà hát Lớn", "address": "",
    "date": FUTURE, "startTime": "19:30", "endTime": "22:00",
    "description": "Đêm nhạc mở màn mùa đông với nhiều nghệ sĩ.\n\nCửa mở lúc 18:30.",
    "tiers": [{"name": "Vé thường", "price": 200000, "quantity": 100, "perks": "Ghế ngồi"},
              {"name": "VIP", "price": "500000", "quantity": "20", "perks": ""}],
}


@pytest.fixture(autouse=True)
def drop_created_events(api_db):
    yield
    api_db.rollback()
    for ev in api_db.scalars(select(Event).where(Event.slug.like("dem-nhac-thu-nghiem%"))):
        drop_org_event(api_db, ev)


def test_create_event_201_pending_with_stock(c, logged_organizer, api_db):
    r = c.post(EVENTS, json=OK)
    assert r.status_code == 201, r.text
    s = r.json()["event"]
    assert s["status"] == "pending" and s["slug"] == "dem-nhac-thu-nghiem" and s["date"] == FUTURE
    assert s["startTime"] == "19:30" and s["capacity"] == 120 and s["minPrice"] == 200000 and s["sold"] == 0
    assert s["orgName"] == "Công ty Sự kiện Thử"
    api_db.expire_all()
    ev = api_db.get(Event, s["id"])
    assert ev.organizer_id == logged_organizer.id and ev.layout == "list" and ev.address == "[ĐỊA CHỈ], Hà Nội"
    assert ev.description == ["Đêm nhạc mở màn mùa đông với nhiều nghệ sĩ.", "Cửa mở lúc 18:30."]
    assert ev.search_text == "dem nhac thu nghiem ha noi nha hat lon nhac song"
    show = api_db.scalars(select(Show).where(Show.event_id == ev.id)).one()
    assert show.id == FUTURE.replace("-", "") + "-1930"
    assert show.starts_at.astimezone(VN).strftime("%H:%M") == "19:30" and show.end_time.strftime("%H:%M") == "22:00"
    tiers = api_db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id).order_by(TicketTier.sort_order)).all()
    assert [(t.id, t.name, t.price, t.capacity, t.max_per_order) for t in tiers] == [
        ("ve-1", "Vé thường", 200000, 100, 10), ("ve-2", "VIP", 500000, 20, 10)]
    stock = {s.tier_id: s.capacity for s in api_db.scalars(select(TierStock).where(TierStock.event_id == ev.id))}
    assert stock == {"ve-1": 100, "ve-2": 20}


def test_pending_event_not_public(c, logged_organizer):
    slug = c.post(EVENTS, json=OK).json()["event"]["slug"]
    assert c.get(f"/api/events/{slug}").status_code == 404
    assert slug not in [e["slug"] for e in c.get("/api/events?organizer=1").json()["events"]]


def test_slug_unique_against_catalog(c, logged_organizer, api_db):
    taken = api_db.scalar(select(Event).where(Event.organizer_id.is_(None)))
    s = c.post(EVENTS, json=OK | {"title": taken.title}).json()["event"]
    try:
        assert s["slug"] == f"{taken.slug}-2"
    finally:
        drop_org_event(api_db, api_db.get(Event, s["id"]))


def test_date_today_accepted_late_evening_vn(c, logged_organizer, monkeypatch):
    late = datetime(2026, 11, 7, 16, 30, tzinfo=timezone.utc)  # 23:30 giờ VN
    monkeypatch.setattr(manage, "now_utc", lambda: late)
    assert c.post(EVENTS, json=OK | {"date": "2026-11-07"}).status_code == 201
    r = c.post(EVENTS, json=OK | {"date": "2026-11-06"})
    assert r.status_code == 400 and r.json() == {"error": "Ngày diễn phải từ hôm nay trở đi"}


T = OK["tiers"][0]
BAD = [
    ({"title": "ab"}, "Tên sự kiện cần từ 3 đến 120 ký tự"),
    ({"title": None}, "Tên sự kiện cần từ 3 đến 120 ký tự"),
    ({"category": "khong-co"}, "Danh mục không hợp lệ"),
    ({"city": "H"}, "Vui lòng nhập thành phố"),
    ({"venue": "N"}, "Vui lòng nhập địa điểm tổ chức"),
    ({"address": "x" * 201}, "Địa chỉ tối đa 200 ký tự"),
    ({"date": "2026-13-40"}, "Ngày diễn không hợp lệ"),
    ({"date": "15/12/2026"}, "Ngày diễn không hợp lệ"),
    ({"date": "2020-01-01"}, "Ngày diễn phải từ hôm nay trở đi"),
    ({"startTime": "25:00"}, "Giờ bắt đầu / kết thúc không hợp lệ"),
    ({"endTime": "7:00"}, "Giờ bắt đầu / kết thúc không hợp lệ"),
    ({"endTime": "19:30"}, "Giờ kết thúc phải sau giờ bắt đầu"),
    ({"description": "ngắn quá"}, "Giới thiệu sự kiện cần từ 20 đến 4000 ký tự"),
    ({"tiers": []}, "Cần từ 1 đến 8 loại vé"),
    ({"tiers": [T] * 9}, "Cần từ 1 đến 8 loại vé"),
    ({"tiers": "abc"}, "Cần từ 1 đến 8 loại vé"),
    ({"tiers": [T | {"name": " "}]}, "Loại vé 1: vui lòng nhập tên"),
    ({"tiers": [T, T | {"name": "x" * 61}]}, "Loại vé 2: vui lòng nhập tên"),
    ({"tiers": [T | {"price": 5000}]}, "Loại vé “Vé thường”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
    ({"tiers": [T | {"price": "abc"}]}, "Loại vé “Vé thường”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
    ({"tiers": [T | {"price": 150000.5}]}, "Loại vé “Vé thường”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
    ({"tiers": [T | {"quantity": 0}]}, "Loại vé “Vé thường”: số lượng từ 1 đến 100.000"),
    ({"tiers": [T | {"quantity": 100001}]}, "Loại vé “Vé thường”: số lượng từ 1 đến 100.000"),
]


@pytest.mark.parametrize("patch,msg", BAD, ids=[f"{list(p)[0]}:{m[:25]}" for p, m in BAD])
def test_create_validation(c, logged_organizer, patch, msg):
    r = c.post(EVENTS, json=OK | patch)
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_customer_cannot_create_403(c, logged_customer):
    assert c.post(EVENTS, json=OK).status_code == 403


def test_me_lists_own_events_with_sales(c, logged_organizer, api_db, auth_db):
    s = c.post(EVENTS, json=OK).json()["event"]
    api_db.execute(update(Event).where(Event.id == s["id"]).values(status="approved", reviewed_at=datetime.now(timezone.utc)))
    api_db.commit()
    buyer = make_customer(api_db, "mua-btc@x.vn")
    show_id = FUTURE.replace("-", "") + "-1930"
    o = insert_order(api_db, buyer, s["slug"], show_id, [("ve-1", 2)])
    body = c.get("/api/organizer/me").json()
    mine = next(e for e in body["events"] if e["id"] == s["id"])
    assert mine["status"] == "approved" and mine["sold"] == 2 and mine["revenue"] == o.total
    r0 = body["recentOrders"][0]
    assert set(r0) == {"id", "total", "created_at", "name", "items"}
    assert r0["id"] == o.id and r0["items"] == "Vé thường ×2" and r0["name"] == "Khách thử" and r0["total"] == o.total


def test_me_does_not_show_other_organizers_events(c, logged_organizer, api_db):
    other = make_org_event(api_db, slug="btc-khac-hoan-toan")
    try:
        assert all(e["slug"] != "btc-khac-hoan-toan" for e in c.get("/api/organizer/me").json()["events"])
    finally:
        drop_org_event(api_db, other)


def test_parallel_creates_with_same_title_all_succeed_with_distinct_slugs(api_db, c, logged_organizer):
    """Bấm gửi 2 lần / mạng chậm gửi lại: không được ra lỗi 500 vì trùng slug"""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from app.main import app
    from tests.booking_helpers import login

    clients = []
    for _ in range(4):
        cl = TestClient(app)
        login(cl, "btc@x.vn")
        clients.append(cl)
    start = threading.Barrier(len(clients))

    def go(cl):
        start.wait()
        return cl.post(EVENTS, json=OK)

    with ThreadPoolExecutor(max_workers=len(clients)) as pool:
        results = list(pool.map(go, clients))
    assert [r.status_code for r in results] == [201] * 4, [r.text for r in results]
    slugs = sorted(r.json()["event"]["slug"] for r in results)
    assert slugs == ["dem-nhac-thu-nghiem", "dem-nhac-thu-nghiem-2", "dem-nhac-thu-nghiem-3", "dem-nhac-thu-nghiem-4"]
