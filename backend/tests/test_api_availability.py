"""GET /api/events/{slug}/availability?show=: vé còn lại theo suất (khớp JSON của API Node cũ)"""
import json
from pathlib import Path

from sqlalchemy import delete, func, select, update

from app.models.catalog import Event, MapSeat, Show
from app.models.sales import Order, SeatHold, TierStock
from app.models.users import User

LEGACY = json.loads((Path(__file__).resolve().parent / "fixtures/legacy_events.json").read_text(encoding="utf-8"))
LIST_EV = next(e for e in LEGACY if e["layout"] == "list")
ZONES_EV = next(e for e in LEGACY if e["layout"] == "zones")
SEATS_EV = next(e for e in LEGACY if e["layout"] == "seats")
MULTI = next(e for e in LEGACY if len(e["shows"]) >= 2)


def url(ev: dict, show: str | None = None) -> str:
    return f"/api/events/{ev['slug']}/availability" + (f"?show={show}" if show else "")


def event_id(db, slug: str) -> int:
    return db.scalar(select(Event.id).where(Event.slug == slug))


def test_zones_remaining_subtracts_presold_and_sold(api, api_db):
    eid, show = event_id(api_db, ZONES_EV["slug"]), ZONES_EV["shows"][0]["id"]
    stock = api_db.scalars(select(TierStock).where(TierStock.event_id == eid, TierStock.show_id == show,
                                                   TierStock.presold + 2 <= TierStock.capacity)).first()
    before = {t["id"]: t["remaining"] for t in api.get(url(ZONES_EV, show)).json()["tiers"]}
    assert before[stock.tier_id] == stock.capacity - stock.presold
    key = (stock.event_id, stock.show_id, stock.tier_id)
    try:
        api_db.execute(update(TierStock).where(TierStock.event_id == key[0], TierStock.show_id == key[1],
                                               TierStock.tier_id == key[2]).values(sold=2))
        api_db.commit()
        after = {t["id"]: t["remaining"] for t in api.get(url(ZONES_EV, show)).json()["tiers"]}
        assert after[stock.tier_id] == before[stock.tier_id] - 2
    finally:
        api_db.execute(update(TierStock).where(TierStock.event_id == key[0], TierStock.show_id == key[1],
                                               TierStock.tier_id == key[2]).values(sold=0))
        api_db.commit()


def test_list_event_remaining_equals_capacity_when_nothing_sold(api, api_db):
    body = api.get(url(LIST_EV)).json()
    eid = event_id(api_db, LIST_EV["slug"])
    caps = dict(api_db.execute(select(TierStock.tier_id, TierStock.capacity).where(
        TierStock.event_id == eid, TierStock.show_id == body["show"])).all())
    assert {t["id"]: t["remaining"] for t in body["tiers"]} == caps


def test_list_event_has_no_unavailable_seats_key(api):
    r = api.get(url(LIST_EV))
    assert r.status_code == 200 and "unavailableSeats" not in r.json()


def test_seats_unavailable_includes_presold_and_sold_holds(api, api_db):
    eid, show = event_id(api_db, SEATS_EV["slug"]), SEATS_EV["shows"][0]["id"]
    body = api.get(url(SEATS_EV, show)).json()
    presold = set(api_db.scalars(select(SeatHold.seat_id).where(SeatHold.event_id == eid, SeatHold.show_id == show)))
    assert set(body["unavailableSeats"]) == presold and body["unavailableSeats"] == sorted(body["unavailableSeats"])

    map_id = api_db.scalar(select(Event.map_id).where(Event.id == eid))
    free_seat = api_db.scalar(select(MapSeat).where(MapSeat.map_id == map_id, MapSeat.id.not_in(presold)).limit(1))
    before = {t["id"]: t["remaining"] for t in body["tiers"]}
    u = User(name="Khách ghế", email="ghe@x.vn", password_hash="h")
    api_db.add(u)
    api_db.flush()
    o = Order(id="TN-GHE0001", user_id=u.id, event_id=eid, show_id=show, subtotal=1, discount=0, total=1,
              method="qr", buyer_name="B", buyer_email="b@x.vn", buyer_phone="0912345678")
    api_db.add(o)
    api_db.flush()
    api_db.add(SeatHold(event_id=eid, show_id=show, seat_id=free_seat.id, order_id=o.id))
    api_db.commit()
    try:
        after = api.get(url(SEATS_EV, show)).json()
        assert free_seat.id in after["unavailableSeats"]
        assert {t["id"]: t["remaining"] for t in after["tiers"]}[free_seat.group_id] == before[free_seat.group_id] - 1
    finally:
        api_db.execute(delete(User).where(User.id == u.id))
        api_db.commit()


def test_seats_remaining_matches_free_seat_count(api, api_db):
    eid, show = event_id(api_db, SEATS_EV["slug"]), SEATS_EV["shows"][0]["id"]
    body = api.get(url(SEATS_EV, show)).json()
    map_id = api_db.scalar(select(Event.map_id).where(Event.id == eid))
    total = api_db.scalar(select(func.count()).select_from(MapSeat).where(MapSeat.map_id == map_id))
    assert sum(t["remaining"] for t in body["tiers"]) == total - len(body["unavailableSeats"])
    assert all(t["remaining"] >= 0 for t in body["tiers"])


def test_default_show_is_earliest_active(api, api_db):
    assert api.get(url(MULTI)).json()["show"] == MULTI["shows"][0]["id"]
    eid = event_id(api_db, MULTI["slug"])
    try:
        api_db.execute(update(Show).where(Show.event_id == eid, Show.id == MULTI["shows"][0]["id"]).values(active=False))
        api_db.commit()
        assert api.get(url(MULTI)).json()["show"] == MULTI["shows"][1]["id"]
    finally:
        api_db.execute(update(Show).where(Show.event_id == eid).values(active=True))
        api_db.commit()


def test_show_of_another_event_is_404(api):
    r = api.get(url(LIST_EV, ZONES_EV["shows"][0]["id"]))
    assert r.status_code == 404 and r.json() == {"error": "Suất diễn không tồn tại"}


def test_inactive_show_is_404(api, api_db):
    eid, show = event_id(api_db, MULTI["slug"]), MULTI["shows"][1]["id"]
    try:
        api_db.execute(update(Show).where(Show.event_id == eid, Show.id == show).values(active=False))
        api_db.commit()
        r = api.get(url(MULTI, show))
        assert r.status_code == 404 and r.json() == {"error": "Suất diễn không tồn tại"}
    finally:
        api_db.execute(update(Show).where(Show.event_id == eid).values(active=True))
        api_db.commit()


def test_unknown_event_404(api):
    r = api.get("/api/events/khong-co/availability")
    assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}
