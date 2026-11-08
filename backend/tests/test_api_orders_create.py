"""POST /api/orders — sự kiện bán theo loại vé / theo khu; chống bán vượt khi mua đồng thời"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text, update

from app.main import app
from app.models.catalog import Event, Show, TicketTier
from app.models.sales import Ticket, TierStock
from tests.api_helpers import drop_org_event, make_org_event, org_show_id
from tests.booking_helpers import LEGACY, event_id, login, make_customer

ORDERS = "/api/orders"
SOON = datetime.now(timezone.utc) + timedelta(days=1)
FUTURE = [e for e in LEGACY if datetime.fromisoformat(e["shows"][0]["start"]) > SOON and e["status"] == "on-sale"]
LIST = next(e for e in FUTURE if e["layout"] == "list")
ZONES = next(e for e in FUTURE if e["layout"] == "zones")
BUYER = {"name": "Khách A", "email": "a@x.vn", "phone": "0912345678"}


def order(ev: dict, **over) -> dict:
    body = {"slug": ev["slug"], "showId": ev["shows"][0]["id"], "items": [{"tierId": ev["tiers"][0]["id"], "qty": 1}],
            "buyer": BUYER, "method": "qr"}
    return body | over


def remaining(client, ev: dict, tier_id: str, show: str | None = None) -> int:
    r = client.get(f"/api/events/{ev['slug']}/availability?show={show or ev['shows'][0]['id']}").json()
    return {t["id"]: t["remaining"] for t in r["tiers"]}[tier_id]


def stock_row(db, ev: dict, tier_id: str) -> TierStock:
    db.expire_all()
    return db.get(TierStock, (event_id(db, ev["slug"]), ev["shows"][0]["id"], tier_id))


@pytest.fixture(autouse=True)
def restore_stock(api_db):
    """Mỗi test trả kho về như vừa nạp (sold = 0, capacity theo hạng vé)"""
    yield
    api_db.rollback()
    api_db.execute(text("UPDATE tier_stock SET sold = 0"))
    api_db.execute(text("UPDATE tier_stock s SET capacity = t.capacity FROM ticket_tiers t "
                        "WHERE t.event_id = s.event_id AND t.id = s.tier_id"))
    api_db.execute(update(Event).values(sale_start=None).where(Event.slug.in_([LIST["slug"], ZONES["slug"]])))
    api_db.commit()


@pytest.fixture
def logged_in(api, api_db, c):
    make_customer(api_db, "a@x.vn")
    login(c, "a@x.vn")
    return c


def clients(api_db, n: int) -> list[TestClient]:
    out = []
    for i in range(n):
        make_customer(api_db, f"song-song-{i}@x.vn")
        cl = TestClient(app)
        login(cl, f"song-song-{i}@x.vn")
        out.append(cl)
    return out


# ------------------------------------------------------------------ đặt vé thành công
def test_create_list_order_201_and_stock_decreases(logged_in):
    tier = LIST["tiers"][0]
    before = remaining(logged_in, LIST, tier["id"])
    r = logged_in.post(ORDERS, json=order(LIST, items=[{"tierId": tier["id"], "qty": 2}]))
    assert r.status_code == 201, r.text
    o = r.json()["order"]
    assert o["total"] == o["subtotal"] == 2 * tier["price"] and o["status"] == "paid" and len(o["tickets"]) == 2
    assert o["buyer"] == BUYER and o["slug"] == LIST["slug"]
    assert remaining(logged_in, LIST, tier["id"]) == before - 2
    assert logged_in.get(ORDERS).json()["orders"][0]["id"] == o["id"]


def test_items_with_same_tier_are_merged(logged_in):
    t = LIST["tiers"][0]["id"]
    o = logged_in.post(ORDERS, json=order(LIST, items=[{"tierId": t, "qty": 1}, {"tierId": t, "qty": 2}])).json()["order"]
    assert o["items"][0]["qty"] == 3 and len(o["tickets"]) == 3


def test_numeric_string_qty_accepted_like_node(logged_in):
    t = LIST["tiers"][0]["id"]
    assert logged_in.post(ORDERS, json=order(LIST, items=[{"tierId": t, "qty": "2"}])).status_code == 201


def test_missing_show_id_uses_first_active_show(logged_in):
    body = order(LIST)
    del body["showId"]
    assert logged_in.post(ORDERS, json=body).json()["order"]["showId"] == LIST["shows"][0]["id"]


def test_zone_order_respects_presold(logged_in, api_db):
    tier = next(t for t in ZONES["tiers"] if t["max"] >= 2)
    s = stock_row(api_db, ZONES, tier["id"])
    api_db.execute(update(TierStock).where(TierStock.event_id == s.event_id, TierStock.show_id == s.show_id,
                                           TierStock.tier_id == s.tier_id).values(capacity=s.presold + 2))
    api_db.commit()
    assert remaining(logged_in, ZONES, tier["id"]) == 2
    assert logged_in.post(ORDERS, json=order(ZONES, items=[{"tierId": tier["id"], "qty": 2}])).status_code == 201
    r = logged_in.post(ORDERS, json=order(ZONES, items=[{"tierId": tier["id"], "qty": 1}]))
    assert r.status_code == 409 and r.json() == {"error": f"{tier['name']} vừa hết vé"}


def test_partial_left_message(logged_in, api_db):
    tier = LIST["tiers"][0]
    s = stock_row(api_db, LIST, tier["id"])
    api_db.execute(update(TierStock).where(TierStock.event_id == s.event_id, TierStock.show_id == s.show_id,
                                           TierStock.tier_id == s.tier_id).values(capacity=3))
    api_db.commit()
    r = logged_in.post(ORDERS, json=order(LIST, items=[{"tierId": tier["id"], "qty": 4}]))
    assert r.status_code == 409 and r.json() == {"error": f"{tier['name']} chỉ còn 3 vé"}


def test_client_prices_are_ignored(logged_in):
    tier = LIST["tiers"][0]
    body = order(LIST, items=[{"tierId": tier["id"], "qty": 1, "price": 1}], total=1, subtotal=1, discount=999999)
    o = logged_in.post(ORDERS, json=body).json()["order"]
    assert o["total"] == tier["price"] and o["discount"] == 0


def test_coupon_lowercase_applies(logged_in):
    tier = max(LIST["tiers"], key=lambda t: t["price"])
    qty = -(-500000 // tier["price"])  # đủ ≥ 500.000 ₫
    o = logged_in.post(ORDERS, json=order(LIST, items=[{"tierId": tier["id"], "qty": qty}], coupon=" nhip50 ")).json()["order"]
    assert o["coupon"] == "NHIP50" and o["discount"] == 50000 and o["total"] == o["subtotal"] - 50000


def test_coupon_min_order_400(logged_in):
    cheap = min(LIST["tiers"], key=lambda t: t["price"])
    assert cheap["price"] < 500000
    r = logged_in.post(ORDERS, json=order(LIST, items=[{"tierId": cheap["id"], "qty": 1}], coupon="NHIP50"))
    assert r.status_code == 400 and r.json() == {"error": "Mã NHIP50 chỉ áp dụng cho đơn từ 500.000 ₫"}


def test_unknown_coupon_400(logged_in):
    r = logged_in.post(ORDERS, json=order(LIST, coupon="KHONGCO"))
    assert r.status_code == 400 and r.json() == {"error": "Mã giảm giá không tồn tại"}


# ------------------------------------------------------------------ kiểm tra dữ liệu
T0 = LIST["tiers"][0]
BAD = [
    ({"slug": "khong-co"}, 404, "Sự kiện không tồn tại"),
    ({"showId": "20990101-0000"}, 400, "Suất diễn không hợp lệ"),
    ({"showId": ZONES["shows"][0]["id"]}, 400, "Suất diễn không hợp lệ"),
    ({"buyer": BUYER | {"name": "A"}}, 400, "Vui lòng nhập họ tên người nhận vé"),
    ({"buyer": BUYER | {"email": "a@b"}}, 400, "Email nhận vé không hợp lệ"),
    ({"buyer": BUYER | {"phone": "123"}}, 400, "Số điện thoại không hợp lệ"),
    ({"buyer": None}, 400, "Vui lòng nhập họ tên người nhận vé"),
    ({"method": "cash"}, 400, "Phương thức thanh toán không hợp lệ"),
    ({"items": [{"tierId": T0["id"], "qty": 0}]}, 400, "Số lượng vé không hợp lệ"),
    ({"items": [{"tierId": T0["id"], "qty": 1.5}]}, 400, "Số lượng vé không hợp lệ"),
    ({"items": [{"tierId": T0["id"], "qty": True}]}, 400, "Số lượng vé không hợp lệ"),
    ({"items": "abc"}, 400, "Vui lòng chọn ít nhất 1 vé"),
    ({"items": []}, 400, "Vui lòng chọn ít nhất 1 vé"),
    ({"items": [{"tierId": "khong-co", "qty": 1}]}, 400, "Hạng vé không hợp lệ"),
    ({"items": [{"tierId": T0["id"], "qty": T0["max"] + 1}]}, 400, f"{T0['name']}: tối đa {T0['max']} vé mỗi đơn"),
    ({"items": [{"tierId": t["id"], "qty": min(t["max"], 4)} for t in LIST["tiers"]]}, 400, "Mỗi đơn tối đa 10 vé"),
]


@pytest.mark.parametrize("patch,status,msg", BAD, ids=[m for _, _, m in BAD])
def test_validation_messages(logged_in, patch, status, msg):
    r = logged_in.post(ORDERS, json=order(LIST, **patch))
    assert r.status_code == status and r.json() == {"error": msg}


def test_requires_login_401(api, c):
    r = c.post(ORDERS, json=order(LIST))
    assert r.status_code == 401 and r.json() == {"error": "Vui lòng đăng nhập để tiếp tục"}


def test_coming_event_400(logged_in, api_db):
    api_db.execute(update(Event).where(Event.slug == LIST["slug"]).values(sale_start=SOON + timedelta(days=3)))
    api_db.commit()
    r = logged_in.post(ORDERS, json=order(LIST))
    assert r.status_code == 400 and r.json() == {"error": "Sự kiện chưa mở bán"}


def test_past_show_400(logged_in, api_db):
    past = next(e for e in LEGACY if e["layout"] == "list" and
                datetime.fromisoformat(e["shows"][-1]["start"]) < datetime.now(timezone.utc))
    r = logged_in.post(ORDERS, json=order(past, showId=past["shows"][-1]["id"]))
    assert r.status_code == 400 and r.json() == {"error": "Suất diễn này đã diễn ra"}


def test_inactive_show_and_tier_rejected(logged_in, api_db):
    eid = event_id(api_db, LIST["slug"])
    try:
        api_db.execute(update(TicketTier).where(TicketTier.event_id == eid, TicketTier.id == T0["id"]).values(active=False))
        api_db.commit()
        assert logged_in.post(ORDERS, json=order(LIST)).json() == {"error": "Hạng vé không hợp lệ"}
        api_db.execute(update(TicketTier).where(TicketTier.event_id == eid).values(active=True))
        api_db.execute(update(Show).where(Show.event_id == eid, Show.id == LIST["shows"][0]["id"]).values(active=False))
        api_db.commit()
        assert logged_in.post(ORDERS, json=order(LIST)).json() == {"error": "Suất diễn không hợp lệ"}
    finally:
        api_db.rollback()
        api_db.execute(update(TicketTier).where(TicketTier.event_id == eid).values(active=True))
        api_db.execute(update(Show).where(Show.event_id == eid).values(active=True))
        api_db.commit()


def test_org_event_without_stock_row_is_bookable(logged_in, api_db):
    ev = make_org_event(api_db, slug="btc-ban-ve", status="approved")
    try:
        body = {"slug": "btc-ban-ve", "showId": org_show_id(ev), "items": [{"tierId": "ve-1", "qty": 3}],
                "buyer": BUYER, "method": "wallet"}
        assert logged_in.post(ORDERS, json=body).status_code == 201
        api_db.expire_all()
        s = api_db.get(TierStock, (ev.id, org_show_id(ev), "ve-1"))
        assert s is not None and s.sold == 3 and s.capacity == 50
    finally:
        drop_org_event(api_db, ev)


def test_multi_tier_order_is_all_or_nothing(logged_in, api_db):
    t1, t2 = LIST["tiers"][0], LIST["tiers"][1]
    s2 = stock_row(api_db, LIST, t2["id"])
    api_db.execute(update(TierStock).where(TierStock.event_id == s2.event_id, TierStock.show_id == s2.show_id,
                                           TierStock.tier_id == t2["id"]).values(capacity=1))
    api_db.commit()
    before = remaining(logged_in, LIST, t1["id"])
    r = logged_in.post(ORDERS, json=order(LIST, items=[{"tierId": t1["id"], "qty": 2}, {"tierId": t2["id"], "qty": 2}]))
    assert r.status_code == 409 and r.json() == {"error": f"{t2['name']} chỉ còn 1 vé"}
    assert remaining(logged_in, LIST, t1["id"]) == before
    assert logged_in.get(ORDERS).json()["orders"] == []


# ------------------------------------------------------------------ mua đồng thời
def test_parallel_buyers_never_oversell(api_db, c):
    tier = LIST["tiers"][0]
    s = stock_row(api_db, LIST, tier["id"])
    api_db.execute(update(TierStock).where(TierStock.event_id == s.event_id, TierStock.show_id == s.show_id,
                                           TierStock.tier_id == tier["id"]).values(capacity=s.presold + 5))
    api_db.commit()
    buyers = clients(api_db, 20)
    body = order(LIST, items=[{"tierId": tier["id"], "qty": 1}])
    with ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(lambda cl: cl.post(ORDERS, json=body).status_code, buyers))
    assert codes.count(201) == 5 and codes.count(409) == 15, codes
    s = stock_row(api_db, LIST, tier["id"])
    assert s.presold + s.sold == s.capacity
    sold_tickets = api_db.scalar(select(func.count()).select_from(Ticket).where(
        Ticket.event_id == s.event_id, Ticket.tier_id == tier["id"]))
    assert sold_tickets == 5


def test_crossed_multi_tier_orders_do_not_deadlock(api_db, c):
    t1, t2 = LIST["tiers"][0]["id"], LIST["tiers"][1]["id"]
    buyers = clients(api_db, 10)
    ab = order(LIST, items=[{"tierId": t1, "qty": 1}, {"tierId": t2, "qty": 1}])
    ba = order(LIST, items=[{"tierId": t2, "qty": 1}, {"tierId": t1, "qty": 1}])
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(lambda p: p[1].post(ORDERS, json=ab if p[0] % 2 else ba).status_code, enumerate(buyers)))
    assert codes == [201] * 10


def test_failed_response_does_not_leave_a_saved_order(logged_in, api_db, monkeypatch):
    """Nếu dựng JSON trả về bị lỗi (500), đơn KHÔNG được lưu — tránh khách bấm mua lại thành mua trùng"""
    from fastapi.testclient import TestClient

    from app.services import booking

    tier = LIST["tiers"][0]
    before = remaining(logged_in, LIST, tier["id"])

    def boom(db, orders):
        raise RuntimeError("lỗi khi dựng JSON")

    monkeypatch.setattr(booking, "orders_json", boom)
    client = TestClient(app, raise_server_exceptions=False, cookies=dict(logged_in.cookies))
    r = client.post(ORDERS, json=order(LIST, items=[{"tierId": tier["id"], "qty": 1}]))
    monkeypatch.undo()
    assert r.status_code == 500
    assert logged_in.get(ORDERS).json()["orders"] == []
    assert remaining(logged_in, LIST, tier["id"]) == before
