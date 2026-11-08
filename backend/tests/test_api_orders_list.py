"""GET /api/orders — JSON giống toOrderJson của server Node; mã đơn / mã vé"""
import re
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.catalog import Event, MapSeat
from app.models.sales import SeatHold
from app.services.booking import ALPHABET, new_order_id, new_ticket_code, random_code
from tests.booking_helpers import LEGACY, event_id, insert_order, login, make_customer

LIST = next(e for e in LEGACY if e["layout"] == "list")
SEATS = next(e for e in LEGACY if e["layout"] == "seats")
KEYS = {"id", "slug", "title", "showId", "start", "startTime", "endTime", "venue", "address", "items", "tickets",
        "subtotal", "discount", "coupon", "total", "method", "status", "buyer", "createdAt",
        "refundedAt", "eventStatus", "cancelReason", "cancelledBy"}  # Task D1: khách biết đơn bị hoàn do huỷ sự kiện


def test_orders_requires_login(api, c):
    r = c.get("/api/orders")
    assert r.status_code == 401 and r.json() == {"error": "Vui lòng đăng nhập để tiếp tục"}


def test_lists_only_own_orders_newest_first(api, api_db, c):
    a = make_customer(api_db, "a@x.vn")
    b = make_customer(api_db, "b@x.vn")
    show = LIST["shows"][0]["id"]
    tier = LIST["tiers"][0]["id"]
    o1 = insert_order(api_db, a, LIST["slug"], show, [(tier, 1)], created_at=datetime(2026, 11, 1, tzinfo=timezone.utc))
    o2 = insert_order(api_db, a, LIST["slug"], show, [(tier, 1)], created_at=datetime(2026, 11, 3, tzinfo=timezone.utc))
    insert_order(api_db, b, LIST["slug"], show, [(tier, 1)])
    login(c, "a@x.vn")
    assert [o["id"] for o in c.get("/api/orders").json()["orders"]] == [o2.id, o1.id]


def test_order_json_shape_matches_node(api, api_db, c):
    u = make_customer(api_db, "a@x.vn")
    show = LIST["shows"][0]
    tier = LIST["tiers"][0]
    o = insert_order(api_db, u, LIST["slug"], show["id"], [(tier["id"], 2)])
    login(c, "a@x.vn")
    body = c.get("/api/orders").json()["orders"][0]
    assert set(body) == KEYS
    assert body["id"] == o.id and body["slug"] == LIST["slug"] and body["title"] == LIST["title"]
    assert body["showId"] == show["id"] and body["start"] == show["start"] and body["start"].endswith("+07:00")
    assert body["startTime"] == show["startTime"] and body["endTime"] == show["endTime"]
    assert body["venue"] == LIST["venue"] and body["address"] == LIST["address"]
    assert body["items"] == [{"tierId": tier["id"], "name": tier["name"], "price": tier["price"], "qty": 2}]
    assert len(body["tickets"]) == 2
    assert (body["refundedAt"], body["eventStatus"], body["cancelReason"], body["cancelledBy"]) == (None, "approved", None, None)
    assert body["tickets"][0] | {"code": "x"} == {"code": "x", "tierId": tier["id"], "name": tier["name"],
                                                    "price": tier["price"], "seat": None, "checkedInAt": None}
    assert body["subtotal"] == body["total"] == 2 * tier["price"] and body["discount"] == 0 and body["coupon"] is None
    assert body["method"] == "qr" and body["status"] == "paid"
    assert body["buyer"] == {"name": "Người nhận", "email": "nhan@x.vn", "phone": "0912345678"}
    assert body["createdAt"].endswith("+07:00")


def test_seat_ticket_has_seat_label(api, api_db, c):
    u = make_customer(api_db, "a@x.vn")
    eid = event_id(api_db, SEATS["slug"])
    show = SEATS["shows"][0]["id"]
    map_id = api_db.scalar(select(Event.map_id).where(Event.id == eid))
    held = select(SeatHold.seat_id).where(SeatHold.event_id == eid, SeatHold.show_id == show)
    seat = api_db.scalar(select(MapSeat).where(MapSeat.map_id == map_id, MapSeat.id.not_in(held)).limit(1))
    insert_order(api_db, u, SEATS["slug"], show, seats=[(seat.group_id, seat.id)])
    login(c, "a@x.vn")
    t = c.get("/api/orders").json()["orders"][0]["tickets"][0]
    assert t["seat"] == seat.label and t["tierId"] == seat.group_id


def test_random_codes_use_unambiguous_alphabet():
    assert set(random_code(500)) <= set(ALPHABET)
    assert not set("IO01") & set(ALPHABET)


def test_order_and_ticket_code_formats(api_db):
    assert re.fullmatch(r"TN[A-Z2-9]{8}", new_order_id(api_db))
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", new_ticket_code(api_db))
