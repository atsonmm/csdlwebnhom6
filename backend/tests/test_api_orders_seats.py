"""POST /api/orders — sự kiện bán theo ghế; chống bán trùng ghế khi mua đồng thời"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.main import app
from app.models.sales import SeatHold
from tests.booking_helpers import LEGACY, event_id, login, make_customer

ORDERS = "/api/orders"
SOON = datetime.now(timezone.utc) + timedelta(days=1)
SEATS = next(e for e in LEGACY if e["layout"] == "seats" and e["status"] == "on-sale"
             and datetime.fromisoformat(e["shows"][0]["start"]) > SOON)
SHOW = SEATS["shows"][0]["id"]
MAP = next(m for m in json.loads((Path(__file__).resolve().parent / "fixtures/legacy_maps.json").read_text(encoding="utf-8"))
           if m["id"] == SEATS["map"])
SEAT_BY_ID = {s["id"]: s for s in MAP["seats"]}
TIER = {t["id"]: t for t in SEATS["tiers"]}
BUYER = {"name": "Khách A", "email": "a@x.vn", "phone": "0912345678"}


def body(seats: list[str], **over) -> dict:
    return {"slug": SEATS["slug"], "showId": SHOW, "seats": seats, "buyer": BUYER, "method": "card"} | over


def unavailable(client) -> set[str]:
    return set(client.get(f"/api/events/{SEATS['slug']}/availability?show={SHOW}").json()["unavailableSeats"])


def free_seats(client, n: int, group: str | None = None) -> list[str]:
    taken = unavailable(client)
    out = [s["id"] for s in MAP["seats"] if s["id"] not in taken and (group is None or s["group"] == group)]
    return out[:n]


@pytest.fixture(autouse=True)
def release_seats(api_db):
    """Trả lại mọi ghế đã bán qua hệ thống trong test (đơn bị xoá cùng tài khoản thử)"""
    yield
    api_db.rollback()
    api_db.execute(delete(SeatHold).where(SeatHold.order_id.is_not(None)))
    api_db.commit()


@pytest.fixture
def logged_in(api, api_db, c):
    make_customer(api_db, "a@x.vn")
    login(c, "a@x.vn")
    return c


def test_seat_order_201_tickets_have_labels(logged_in):
    picked = free_seats(logged_in, 2)
    r = logged_in.post(ORDERS, json=body(picked))
    assert r.status_code == 201, r.text
    o = r.json()["order"]
    assert sorted(t["seat"] for t in o["tickets"]) == sorted(SEAT_BY_ID[s]["label"] for s in picked)
    assert o["subtotal"] == sum(TIER[SEAT_BY_ID[s]["group"]]["price"] for s in picked)
    assert set(picked) <= unavailable(logged_in)


def test_seats_grouped_into_tiers(logged_in):
    a = free_seats(logged_in, 1, "gold") + free_seats(logged_in, 2, "silver")
    o = logged_in.post(ORDERS, json=body(a)).json()["order"]
    assert {i["tierId"]: i["qty"] for i in o["items"]} == {"gold": 1, "silver": 2}


def test_presold_seat_409_with_label(logged_in):
    taken = sorted(unavailable(logged_in))[0]
    s = SEAT_BY_ID[taken]
    r = logged_in.post(ORDERS, json=body([taken]))
    assert r.status_code == 409 and r.json() == {"error": f"Ghế {s['row']}{s['num']} ({s['label']}) vừa có người mua"}


@pytest.mark.parametrize("seats,msg", [
    ([], "Vui lòng chọn ít nhất 1 ghế"),
    ("G-D5", "Vui lòng chọn ít nhất 1 ghế"),
    (["X-Z99"], "Ghế không hợp lệ"),
    ([5], "Ghế không hợp lệ"),
])
def test_seat_validation(logged_in, seats, msg):
    r = logged_in.post(ORDERS, json=body(seats))
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_more_than_10_seats_400(logged_in):
    r = logged_in.post(ORDERS, json=body(free_seats(logged_in, 11)))
    assert r.status_code == 400 and r.json() == {"error": "Mỗi đơn tối đa 10 vé"}


def test_duplicate_seat_ids_in_request_count_once(logged_in):
    s = free_seats(logged_in, 1)[0]
    o = logged_in.post(ORDERS, json=body([s, s])).json()["order"]
    assert len(o["tickets"]) == 1


def test_coupon_on_seat_order(logged_in):
    picked = free_seats(logged_in, 10, "diamond") or free_seats(logged_in, 10)
    picked = picked[: max(1, -(-500000 // TIER[SEAT_BY_ID[picked[0]]["group"]]["price"]))]
    o = logged_in.post(ORDERS, json=body(picked, coupon="NHIP50")).json()["order"]
    assert o["discount"] == 50000 and o["total"] == o["subtotal"] - 50000


def test_seat_event_rejects_show_of_other_event(logged_in):
    other = next(e for e in LEGACY if e["slug"] != SEATS["slug"])
    r = logged_in.post(ORDERS, json=body(free_seats(logged_in, 1), showId=other["shows"][0]["id"]))
    assert r.status_code == 400 and r.json() == {"error": "Suất diễn không hợp lệ"}


def _buyers(api_db, n: int) -> list[TestClient]:
    out = []
    for i in range(n):
        make_customer(api_db, f"ghe-{i}@x.vn")
        cl = TestClient(app)
        login(cl, f"ghe-{i}@x.vn")
        out.append(cl)
    return out


def test_parallel_same_seat_exactly_one_wins(api_db, c):
    seat = free_seats(c, 1)[0]
    buyers = _buyers(api_db, 10)
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(lambda cl: cl.post(ORDERS, json=body([seat])).status_code, buyers))
    assert codes.count(201) == 1 and codes.count(409) == 9, codes
    eid = event_id(api_db, SEATS["slug"])
    held = api_db.scalar(select(func.count()).select_from(SeatHold).where(
        SeatHold.event_id == eid, SeatHold.show_id == SHOW, SeatHold.seat_id == seat))
    assert held == 1


def test_parallel_overlapping_seat_sets_no_double_sale(api_db, c):
    row = free_seats(c, 9)                       # 9 ghế trống → 8 cặp chồng nhau: (0,1), (1,2), …
    pairs = [[row[i], row[i + 1]] for i in range(8)]
    buyers = _buyers(api_db, 8)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda p: p[1].post(ORDERS, json=body(p[0])), zip(pairs, buyers)))
    won = [r.json()["order"] for r in results if r.status_code == 201]
    assert all(r.status_code in (201, 409) for r in results)
    sold = [t["seat"] for o in won for t in o["tickets"]]
    assert len(sold) == len(set(sold)) == 2 * len(won) and won
    eid = event_id(api_db, SEATS["slug"])
    by_system = api_db.scalar(select(func.count()).select_from(SeatHold).where(
        SeatHold.event_id == eid, SeatHold.show_id == SHOW, SeatHold.order_id.is_not(None)))
    assert by_system == 2 * len(won)


def test_parallel_crossed_seat_pairs_get_seat_message_not_busy(api_db, c):
    """[A,B] và [B,A] cùng lúc: không được deadlock — người thua phải nhận 409 nêu tên ghế"""
    import threading

    a, b = free_seats(c, 2)
    buyers = _buyers(api_db, 8)
    start = threading.Barrier(len(buyers))

    def go(p):
        i, cl = p
        start.wait()
        return cl.post(ORDERS, json=body([a, b] if i % 2 else [b, a]))

    with ThreadPoolExecutor(max_workers=len(buyers)) as pool:
        results = list(pool.map(go, enumerate(buyers)))
    codes = [r.status_code for r in results]
    assert codes.count(201) == 1, codes
    losers = [r.json()["error"] for r in results if r.status_code != 201]
    assert all(r.status_code == 409 for r in results if r.status_code != 201)
    assert all(m.startswith("Ghế ") for m in losers), losers


def test_seat_holds_inserted_in_sorted_seat_order(logged_in, engine):
    """Khoá ghế theo thứ tự mã ghế cố định → hai đơn [A,B] / [B,A] không thể deadlock
    (khe thời gian quá hẹp để tái hiện bằng HTTP, nên chốt trực tiếp thứ tự trong câu INSERT gửi tới PostgreSQL)"""
    from sqlalchemy import event

    a, b = sorted(free_seats(logged_in, 2))
    seen: list[list[str]] = []

    def capture(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO SEAT_HOLDS") and isinstance(params, dict):
            seen.append([v for k, v in sorted(params.items(), key=lambda kv: int(kv[0].rsplit("_m", 1)[1]))
                         if k.startswith("seat_id")])

    event.listen(engine, "before_cursor_execute", capture)
    try:
        assert logged_in.post(ORDERS, json=body([b, a])).status_code == 201
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert seen == [[a, b]]
