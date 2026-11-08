"""Task F4 — sửa sự kiện bán theo sơ đồ (PATCH /api/organizer/events/{id}): full đổi được kiểu bán / sơ đồ / giá;
limited chỉ đổi giá nhóm chưa bán, khoá kiểu bán và sơ đồ"""
from sqlalchemy import func, select

from app.models.catalog import Event, MapGroup, MapSeat, MapZone, TicketTier
from app.models.sales import TierStock
from tests.booking_helpers import insert_order, make_customer
from tests.test_api_org_edit import EVENTS, approve, create, detail, drop_created, form_body, patch  # noqa: F401 (drop_created: fixture tự dọn)


def prices_for(api_db, map_id: str, price: int = 300000) -> dict:
    return {g: price for g in api_db.scalars(select(MapGroup.id).where(MapGroup.map_id == map_id))}


def map_body(c, eid, map_id, prices, layout):
    return form_body(c, eid, layout=layout) | {"mapId": map_id, "prices": prices}


def test_full_edit_switch_list_to_seats(c, logged_organizer, api_db):
    s = create(c)
    prices = prices_for(api_db, "nha-hat-lon", 450000)
    r = patch(c, s["id"], map_body(c, s["id"], "nha-hat-lon", prices, "seats"))
    assert r.status_code == 200, r.text
    api_db.expire_all()
    ev = api_db.get(Event, s["id"])
    assert (ev.layout, ev.map_id) == ("seats", "nha-hat-lon")
    seat_cap = dict(api_db.execute(select(MapSeat.group_id, func.count()).where(MapSeat.map_id == "nha-hat-lon")
                                   .group_by(MapSeat.group_id)).all())
    tiers = {t.id: t for t in api_db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id))}
    assert set(tiers) == set(seat_cap) and all(t.price == 450000 for t in tiers.values())
    assert api_db.scalar(select(func.count()).select_from(TierStock).where(TierStock.event_id == ev.id)) == 0
    f = detail(c, s["id"])["form"]
    assert f["layout"] == "seats" and f["mapId"] == "nha-hat-lon" and set(f["prices"]) == set(seat_cap)


def test_full_edit_switch_zones_to_list(c, logged_organizer, api_db):
    s = create(c, layout="zones", mapId="arena", prices=prices_for(api_db, "arena"))
    body = form_body(c, s["id"], layout="list")
    body["tiers"] = [{"name": "Vé thường", "price": 250000, "quantity": 80, "perks": ""}]
    r = patch(c, s["id"], body)
    assert r.status_code == 200, r.text
    api_db.expire_all()
    ev = api_db.get(Event, s["id"])
    assert (ev.layout, ev.map_id) == ("list", None)
    stock = api_db.scalars(select(TierStock).where(TierStock.event_id == ev.id)).all()
    assert [(st.tier_id, st.capacity) for st in stock] == [("ve-1", 80)]


def test_limited_map_event_price_rules(c, logged_organizer, api_db):
    prices = prices_for(api_db, "arena")
    s = create(c, layout="zones", mapId="arena", prices=prices)
    approve(api_db, s["id"])
    groups = api_db.scalars(select(MapGroup).where(MapGroup.map_id == "arena").order_by(MapGroup.sort_order)).all()
    sold_g, free_g = groups[0], groups[1]
    zone = api_db.scalars(select(MapZone).where(MapZone.map_id == "arena", MapZone.group_id == sold_g.id)).first()
    show = api_db.scalar(select(TierStock.show_id).where(TierStock.event_id == s["id"]).limit(1))
    insert_order(api_db, make_customer(api_db, "khach-sua-so-do@x.vn"), s["slug"], show, [(zone.id, 1)])
    api_db.commit()
    assert detail(c, s["id"])["editable"]["mode"] == "limited"

    ok = patch(c, s["id"], map_body(c, s["id"], "arena", prices | {free_g.id: 777000}, "zones"))
    assert ok.status_code == 200, ok.text
    api_db.expire_all()
    changed = api_db.scalars(select(TicketTier.price).where(TicketTier.event_id == s["id"],
                                                            TicketTier.group_id == free_g.id)).all()
    assert changed and set(changed) == {777000}
    cap_before = api_db.scalar(select(func.sum(TierStock.capacity)).where(TierStock.event_id == s["id"]))

    r = patch(c, s["id"], map_body(c, s["id"], "arena", prices | {free_g.id: 777000, sold_g.id: 999000}, "zones"))
    assert r.status_code == 409 and r.json() == {"error": f"Nhóm “{sold_g.label}” đã có người mua, không đổi được giá"}
    r = patch(c, s["id"], map_body(c, s["id"], "hall-grid", prices_for(api_db, "hall-grid"), "zones"))
    assert r.status_code == 409 and r.json() == {"error": "Sự kiện đã duyệt không thể đổi sơ đồ"}
    body = form_body(c, s["id"], layout="list")
    body["tiers"] = [{"name": "Vé thường", "price": 250000, "quantity": 80, "perks": ""}]
    r = patch(c, s["id"], body)
    assert r.status_code == 409 and r.json() == {"error": "Sự kiện đã duyệt không thể đổi kiểu bán vé"}
    api_db.expire_all()
    assert api_db.scalar(select(func.sum(TierStock.capacity)).where(TierStock.event_id == s["id"])) == cap_before


def test_limited_list_event_cannot_switch_to_map(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    r = patch(c, s["id"], map_body(c, s["id"], "arena", prices_for(api_db, "arena"), "zones"))
    assert r.status_code == 409 and r.json() == {"error": "Sự kiện đã duyệt không thể đổi kiểu bán vé"}
