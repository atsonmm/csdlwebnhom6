"""Task C3 — GET /api/admin/tickets/{code}: tra cứu mã vé toàn sàn, chỉ xem (không soát)"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.sales import Ticket
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer


@pytest.fixture
def desk(c, api, api_db, auth_db):
    ev = make_org_event(api_db, slug="tra-ma-ve", reviewed_at=datetime.now(timezone.utc) - timedelta(days=2))
    buyer = make_customer(api_db, "khach-tra@x.vn")
    o = insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", 2)])
    o.buyer_name = "Phạm Khoa"
    admin = make_customer(api_db, "quantri-tra@x.vn")
    admin.role = "admin"
    api_db.commit()
    codes = api_db.scalars(select(Ticket.code).where(Ticket.order_id == o.id).order_by(Ticket.code)).all()
    login(c, admin.email)
    yield {"ev": ev, "order": o, "codes": codes}
    drop_org_event(api_db, ev)


def test_lookup_any_org_ticket(c, desk):
    body = c.get(f"/api/admin/tickets/{desk['codes'][0].lower()}").json()
    assert set(body) == {"ticket", "order", "event"}
    assert body["ticket"]["code"] == desk["codes"][0] and body["ticket"]["tierName"] == "Vé thường"
    assert body["ticket"]["checkedInAt"] is None and body["ticket"]["buyerName"] == "Phạm Khoa"
    o = desk["order"]
    assert body["order"] == {"id": o.id, "status": "paid", "total": o.total, "createdAt": body["order"]["createdAt"],
                             "buyerName": "Phạm Khoa", "buyerEmail": o.buyer_email}
    assert body["order"]["createdAt"].endswith("+07:00")
    ev = desk["ev"]
    assert body["event"] == {"id": ev.id, "title": ev.title, "slug": ev.slug, "status": "approved",
                             "orgName": "Đơn vị tra-ma-ve"}


def test_lookup_does_not_check_in(c, desk, api_db):
    c.get(f"/api/admin/tickets/{desk['codes'][0]}")
    api_db.expire_all()
    assert api_db.scalar(select(Ticket.checked_in_at).where(Ticket.code == desk["codes"][0])) is None


def test_lookup_refunded_shows_status(c, desk, api_db):
    desk["order"].status = "refunded"
    api_db.commit()
    body = c.get(f"/api/admin/tickets/{desk['codes'][1]}").json()
    assert body["order"]["status"] == "refunded"


def test_bad_code_400_unknown_404(c, desk):
    r = c.get("/api/admin/tickets/abc")
    assert r.status_code == 400 and r.json() == {"error": "Mã vé không hợp lệ"}
    r = c.get("/api/admin/tickets/ZZZZ-ZZZZ")
    assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy vé"}


def test_requires_admin(c, logged_organizer):
    assert c.get("/api/admin/tickets/ZZZZ-ZZZZ").status_code == 403
