"""Task F1 — Ban tổ chức bán theo sơ đồ có sẵn: GET /api/organizer/venue-maps + tạo sự kiện zones / seats"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, update

from app.models.catalog import Event, MapGroup, MapSeat, MapZone, TicketTier
from app.models.sales import TierStock
from app.utils.timefmt import VN
from tests.api_helpers import drop_event
from tests.booking_helpers import login, make_customer

EVENTS = "/api/organizer/events"
FUTURE = (datetime.now(VN) + timedelta(days=30)).date().isoformat()
BASE = {
    "title": "Đêm Sơ Đồ Thử", "category": "nhac-song", "city": "Hà Nội", "venue": "Nhà hát Lớn", "address": "",
    "date": FUTURE, "startTime": "19:30", "endTime": "22:00",
    "description": "Sự kiện thử bán theo sơ đồ có sẵn của sàn.",
}
BUYER = {"name": "Khách A", "email": "a@x.vn", "phone": "0912345678"}


def prices_for(api_db, map_id: str, price: int = 300000) -> dict:
    return {g: price for g in api_db.scalars(select(MapGroup.id).where(MapGroup.map_id == map_id))}


@pytest.fixture(autouse=True)
def drop_created(api_db):
    yield
    api_db.rollback()
    for ev in api_db.scalars(select(Event).where(Event.slug.like("dem-so-do-thu%"))).all():
        drop_event(api_db, ev)  # giữ BTC (đăng nhập) — auth_db dọn tài khoản sau


def test_list_venue_maps_with_group_capacity(c, logged_organizer, api_db):
    r = c.get("/api/organizer/venue-maps")
    assert r.status_code == 200, r.text
    maps = {m["id"]: m for m in r.json()["maps"]}
    assert {"arena", "nha-hat-lon"} <= set(maps)
    arena = maps["arena"]
    assert arena["kind"] == "zones" and set(arena) == {"id", "kind", "name", "capacity", "groups"}
    zone_cap = dict(api_db.execute(select(MapZone.group_id, func.sum(MapZone.capacity)).where(MapZone.map_id == "arena")
                                   .group_by(MapZone.group_id)).all())
    assert {g["id"]: g["capacity"] for g in arena["groups"]} == {k: int(v) for k, v in zone_cap.items()}
    assert arena["capacity"] == sum(zone_cap.values())
    order = list(api_db.scalars(select(MapGroup.id).where(MapGroup.map_id == "arena").order_by(MapGroup.sort_order, MapGroup.id)))
    assert [g["id"] for g in arena["groups"]] == order
    assert set(arena["groups"][0]) == {"id", "label", "color", "capacity", "maxPerOrder", "perks"}
    seat_cap = dict(api_db.execute(select(MapSeat.group_id, func.count()).where(MapSeat.map_id == "nha-hat-lon")
                                   .group_by(MapSeat.group_id)).all())
    assert {g["id"]: g["capacity"] for g in maps["nha-hat-lon"]["groups"]} == seat_cap


def test_venue_maps_requires_organizer(c, logged_customer):
    assert c.get("/api/organizer/venue-maps").status_code == 403


def test_create_zones_event_tiers_and_stock(c, logged_organizer, api_db):
    prices = prices_for(api_db, "arena") | {"fanzone": 2_500_000}
    r = c.post(EVENTS, json=BASE | {"layout": "zones", "mapId": "arena", "prices": prices, "tiers": [{"name": "bỏ qua"}]})
    assert r.status_code == 201, r.text
    s = r.json()["event"]
    api_db.expire_all()
    ev = api_db.get(Event, s["id"])
    assert (ev.layout, ev.map_id) == ("zones", "arena")
    zones = api_db.scalars(select(MapZone).where(MapZone.map_id == "arena")).all()
    tiers = {t.id: t for t in api_db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id))}
    assert set(tiers) == {z.id for z in zones}  # mỗi khu một hạng (quy ước catalog)
    groups = {g.id: g for g in api_db.scalars(select(MapGroup).where(MapGroup.map_id == "arena"))}
    for z in zones:
        t = tiers[z.id]
        assert (t.name, t.capacity, t.group_id, t.price) == (z.label, z.capacity, z.group_id, prices[z.group_id])
        assert t.max_per_order == (groups[z.group_id].max_per_order or 10) and t.perks == groups[z.group_id].perks
    stock = api_db.scalars(select(TierStock).where(TierStock.event_id == ev.id)).all()
    assert {st.tier_id: st.capacity for st in stock} == {z.id: z.capacity for z in zones}
    assert s["capacity"] == sum(z.capacity for z in zones)


def test_create_seats_event_no_tier_stock(c, logged_organizer, api_db):
    prices = prices_for(api_db, "nha-hat-lon")
    r = c.post(EVENTS, json=BASE | {"layout": "seats", "mapId": "nha-hat-lon", "prices": prices})
    assert r.status_code == 201, r.text
    ev_id = r.json()["event"]["id"]
    api_db.expire_all()
    tiers = {t.id: t for t in api_db.scalars(select(TicketTier).where(TicketTier.event_id == ev_id))}
    seat_cap = dict(api_db.execute(select(MapSeat.group_id, func.count()).where(MapSeat.map_id == "nha-hat-lon")
                                   .group_by(MapSeat.group_id)).all())
    assert set(tiers) == set(seat_cap)  # mỗi nhóm ghế một hạng, id = mã nhóm
    assert all(t.group_id == t.id and t.capacity == seat_cap[t.id] for t in tiers.values())
    assert api_db.scalar(select(func.count()).select_from(TierStock).where(TierStock.event_id == ev_id)) == 0
    assert r.json()["event"]["capacity"] == sum(seat_cap.values())  # sức chứa qua kho chung (đếm ghế)


@pytest.mark.parametrize("change, msg", [
    (lambda p: {k: v for k, v in list(p.items())[1:]}, "Nhóm “{label}”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
    (lambda p: p | {next(iter(p)): 9_999}, "Nhóm “{label}”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
    (lambda p: p | {next(iter(p)): 100_000_001}, "Nhóm “{label}”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
    (lambda p: p | {next(iter(p)): "abc"}, "Nhóm “{label}”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
    (lambda p: "khong-phai-dict", "Nhóm “{label}”: giá từ 10.000 ₫ đến 100.000.000 ₫"),
])
def test_missing_or_bad_price_400(c, logged_organizer, api_db, change, msg):
    prices = dict(sorted(prices_for(api_db, "arena").items(),
                         key=lambda kv: api_db.scalar(select(MapGroup.sort_order).where(MapGroup.map_id == "arena",
                                                                                        MapGroup.id == kv[0]))))
    first = api_db.scalars(select(MapGroup).where(MapGroup.map_id == "arena").order_by(MapGroup.sort_order, MapGroup.id)).first()
    r = c.post(EVENTS, json=BASE | {"layout": "zones", "mapId": "arena", "prices": change(prices)})
    assert r.status_code == 400 and r.json() == {"error": msg.format(label=first.label)}


@pytest.mark.parametrize("layout, map_id", [("zones", "nha-hat-lon"), ("seats", "arena"), ("zones", "khong-co"),
                                            ("zones", None), ("seats", 12)])
def test_map_kind_mismatch_400(c, logged_organizer, api_db, layout, map_id):
    r = c.post(EVENTS, json=BASE | {"layout": layout, "mapId": map_id, "prices": prices_for(api_db, "arena")})
    assert r.status_code == 400 and r.json() == {"error": "Sơ đồ không hợp lệ"}


def test_bad_layout_400(c, logged_organizer):
    r = c.post(EVENTS, json=BASE | {"layout": "ve-dung"})
    assert r.status_code == 400 and r.json() == {"error": "Kiểu bán vé không hợp lệ"}


def _approve(api_db, ev_id):
    api_db.execute(update(Event).where(Event.id == ev_id).values(status="approved",
                                                                 reviewed_at=datetime.now(timezone.utc) - timedelta(hours=1)))
    api_db.commit()


def test_created_map_event_bookable_after_approve(c, logged_organizer, api_db, auth_db):
    zones = c.post(EVENTS, json=BASE | {"layout": "zones", "mapId": "arena", "prices": prices_for(api_db, "arena")}).json()["event"]
    seats = c.post(EVENTS, json=BASE | {"title": "Đêm Sơ Đồ Thử Ghế", "layout": "seats", "mapId": "nha-hat-lon",
                                        "prices": prices_for(api_db, "nha-hat-lon", 450000)}).json()["event"]
    _approve(api_db, zones["id"])
    _approve(api_db, seats["id"])
    buyer = make_customer(api_db, "khach-so-do@x.vn")
    login(c, buyer.email)

    zone = api_db.scalars(select(MapZone).where(MapZone.map_id == "arena").order_by(MapZone.sort_order)).first()
    show = c.get(f"/api/events/{zones['slug']}").json()["shows"][0]["id"]
    before = c.get(f"/api/events/{zones['slug']}/availability", params={"show": show}).json()
    r = c.post("/api/orders", json={"slug": zones["slug"], "showId": show, "items": [{"tierId": zone.id, "qty": 2}],
                                    "method": "qr", "buyer": BUYER})
    assert r.status_code == 201, r.text
    after = c.get(f"/api/events/{zones['slug']}/availability", params={"show": show}).json()
    assert before != after  # còn lại của khu vừa mua giảm

    seat = api_db.scalars(select(MapSeat.id).where(MapSeat.map_id == "nha-hat-lon").order_by(MapSeat.id)).first()
    sshow = c.get(f"/api/events/{seats['slug']}").json()["shows"][0]["id"]
    r = c.post("/api/orders", json={"slug": seats["slug"], "showId": sshow, "seats": [seat], "method": "card",
                                    "buyer": BUYER})
    assert r.status_code == 201, r.text
    taken = c.get(f"/api/events/{seats['slug']}/availability", params={"show": sshow}).json()["unavailableSeats"]
    assert seat in taken
    assert r.json()["order"]["total"] == 450000
