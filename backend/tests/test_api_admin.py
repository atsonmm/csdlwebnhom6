"""GET /api/admin/overview, POST /api/admin/events/{id}/review"""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models.catalog import Event
from app.models.sales import Order, Ticket
from app.models.users import Organizer, User
from tests.api_helpers import drop_org_event, make_org_event, org_show_id
from tests.booking_helpers import insert_order, login, make_customer

OVERVIEW = "/api/admin/overview"


def review(client, event_id, decision="approve", reason=""):
    return client.post(f"/api/admin/events/{event_id}/review", json={"decision": decision, "reason": reason})


@pytest.fixture
def pending(api_db):
    ev = make_org_event(api_db, slug="btc-cho-duyet-admin", status="pending")
    yield ev
    drop_org_event(api_db, ev)


def test_overview_requires_admin(c, logged_organizer):
    assert c.get(OVERVIEW).status_code == 403


def test_overview_requires_login(api, c):
    assert c.get(OVERVIEW).status_code == 401


def test_overview_shape_and_totals(c, logged_admin, api_db, pending):
    buyer = make_customer(api_db, "mua-admin@x.vn")
    approved = make_org_event(api_db, slug="btc-da-duyet-admin", status="approved")
    try:
        o = insert_order(api_db, buyer, "btc-da-duyet-admin", org_show_id(approved), [("ve-1", 3)])
        body = c.get(OVERVIEW).json()
        assert set(body) == {"pending", "orders", "totals", "pendingWithdrawals"}
        assert [p["slug"] for p in body["pending"]] == ["btc-cho-duyet-admin"]
        first = body["orders"][0]
        assert set(first) == {"id", "event", "amount", "status", "createdAt", "customer", "tickets"}
        assert first["id"] == o.id and first["event"] == approved.title and first["amount"] == o.total
        assert first["customer"] == "Khách thử" and first["tickets"] == 3 and first["status"] == "paid"
        t = body["totals"]
        assert t["revenue"] == api_db.scalar(select(func.sum(Order.total)).where(Order.status == "paid"))
        paid = Order.status == "paid"
        assert t["orders"] == api_db.scalar(select(func.count()).select_from(Order).where(paid))
        assert t["tickets"] == api_db.scalar(select(func.count()).select_from(Ticket)
                                             .join(Order, Order.id == Ticket.order_id).where(paid))
        assert t["customers"] == api_db.scalar(select(func.count()).select_from(User).where(User.role == "customer"))
        assert t["organizers"] == api_db.scalar(select(func.count()).select_from(Organizer))
        assert t["approvedEvents"] == 1
    finally:
        drop_org_event(api_db, approved)


def test_approve_makes_event_public_and_bookable(c, logged_admin, api_db, pending):
    r = review(c, pending.id)
    assert r.status_code == 200 and r.json() == {"ok": True, "slug": "btc-cho-duyet-admin", "status": "approved"}
    assert "btc-cho-duyet-admin" in [e["slug"] for e in c.get("/api/events?organizer=1").json()["events"]]
    api_db.expire_all()
    assert api_db.get(Event, pending.id).reviewed_at is not None
    make_customer(api_db, "mua-sau-duyet@x.vn")
    buyer = TestClient(app)
    login(buyer, "mua-sau-duyet@x.vn")
    r = buyer.post("/api/orders", json={"slug": "btc-cho-duyet-admin", "items": [{"tierId": "ve-1", "qty": 1}],
                                        "buyer": {"name": "Khách B", "email": "b@x.vn", "phone": "0912345679"},
                                        "method": "qr"})
    assert r.status_code == 201, r.text


def test_reject_with_default_reason(c, logged_admin, api_db, pending):
    r = review(c, pending.id, "reject", "   ")
    assert r.json() == {"ok": True, "slug": "btc-cho-duyet-admin", "status": "rejected"}
    api_db.expire_all()
    assert api_db.get(Event, pending.id).reject_reason == "Hồ sơ chưa đủ thông tin, vui lòng bổ sung."
    assert c.get("/api/events/btc-cho-duyet-admin").status_code == 404


def test_reject_reason_trimmed_to_300(c, logged_admin, api_db, pending):
    review(c, pending.id, "reject", "x" * 400)
    api_db.expire_all()
    assert api_db.get(Event, pending.id).reject_reason == "x" * 300


def test_second_review_409(c, logged_admin, pending):
    review(c, pending.id)
    r = review(c, pending.id, "reject")
    assert r.status_code == 409 and r.json() == {"error": "Hồ sơ này đã được xử lý"}


def test_unknown_catalog_or_bad_id_404(c, logged_admin, api_db):
    catalog_id = api_db.scalar(select(Event.id).where(Event.organizer_id.is_(None)))
    for eid in (999999, catalog_id, "abc"):
        r = review(c, eid)
        assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy hồ sơ sự kiện"}, eid


def test_bad_decision_400(c, logged_admin, pending):
    r = review(c, pending.id, "maybe")
    assert r.status_code == 400 and r.json() == {"error": "Quyết định không hợp lệ"}


def test_review_requires_admin(c, logged_organizer, pending):
    assert review(c, pending.id).status_code == 403


def test_parallel_reviews_exactly_one_wins(api_db, c, pending):
    event_id = pending.id  # đọc trước: object ORM gắn session api_db, không được dùng chung giữa các luồng
    admins = []
    for i in range(6):
        u = make_customer(api_db, f"quantri-{i}@x.vn")
        u.role = "admin"
        api_db.commit()
        cl = TestClient(app)
        login(cl, f"quantri-{i}@x.vn")
        admins.append(cl)
    start = threading.Barrier(len(admins))

    def go(p):
        i, cl = p
        start.wait()
        return review(cl, event_id, "approve" if i % 2 else "reject").status_code

    with ThreadPoolExecutor(max_workers=len(admins)) as pool:
        codes = list(pool.map(go, enumerate(admins)))
    assert sorted(codes) == [200] + [409] * 5, codes


def test_out_of_range_or_non_ascii_ids_are_404(c, logged_admin):
    for eid in ("2147483648", "99999999999999999999", "١٢"):
        r = review(c, eid)
        assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy hồ sơ sự kiện"}, eid
