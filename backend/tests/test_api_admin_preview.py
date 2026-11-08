"""Task F3 — Admin xem trước hồ sơ (GET /api/admin/events/{id}, mọi trạng thái) + chặn duyệt khi đã qua giờ diễn"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, MapGroup
from app.utils.timefmt import VN
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import login, make_customer

FUTURE = (datetime.now(VN) + timedelta(days=30)).date().isoformat()
FORM = {"title": "Hồ Sơ Xem Trước", "category": "nhac-song", "city": "Hà Nội", "venue": "Nhà hát Lớn", "address": "",
        "date": FUTURE, "startTime": "19:30", "endTime": "22:00",
        "description": "Hồ sơ sự kiện chờ duyệt để Admin xem trước."}


@pytest.fixture
def desk(c, api, api_db, auth_db):
    made = []

    def event(slug, **kw):
        ev = make_org_event(api_db, slug=slug, **kw)
        made.append(ev)
        return ev

    admin = make_customer(api_db, "quantri-xem@x.vn")
    admin.role = "admin"
    api_db.commit()
    login(c, admin.email)
    yield {"event": event, "admin": admin}
    api_db.rollback()
    for ev in made:
        api_db.expire_all()
        if api_db.get(Event, ev.id) is not None:
            drop_org_event(api_db, ev)


def test_preview_pending_event_same_shape_as_public(c, desk, api_db):
    pending = desk["event"]("xem-truoc-cho", status="pending")
    public = desk["event"]("xem-truoc-cong-khai", reviewed_at=datetime.now(timezone.utc) - timedelta(days=1))
    r = c.get(f"/api/admin/events/{pending.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"event", "summary", "organizer"}
    shape = c.get(f"/api/events/{public.slug}").json()
    assert set(body["event"]) == set(shape)  # cùng JSON với trang khán giả
    assert body["event"]["slug"] == pending.slug and body["event"]["related"] == []
    assert body["summary"]["phase"] == "pending" and body["summary"]["id"] == pending.id
    assert body["organizer"] == {"orgName": "Đơn vị xem-truoc-cho", "code": f"ORG-{pending.organizer_id:05d}",
                                 "email": "xem-truoc-cho@btc.vn", "phone": "0912345678"}


@pytest.mark.parametrize("status", ["rejected", "cancelled"])
def test_preview_any_status(c, desk, api_db, status):
    ev = desk["event"](f"xem-truoc-{status}")
    values = {"status": status}
    if status == "cancelled":
        values |= {"cancel_reason": "x", "cancelled_at": datetime.now(timezone.utc), "cancelled_by": "admin"}
    api_db.execute(update(Event).where(Event.id == ev.id).values(**values))
    api_db.commit()
    r = c.get(f"/api/admin/events/{ev.id}")
    assert r.status_code == 200 and r.json()["summary"]["phase"] == status


def test_preview_map_event_has_map_and_tiers(c, desk, api_db):
    org = desk["event"]("xem-truoc-so-do-btc")
    from app.services import manage
    from app.schemas.manage import OrgEventIn
    from app.models.users import User

    prices = {g: 500000 for g in api_db.scalars(select(MapGroup.id).where(MapGroup.map_id == "arena"))}
    ev = manage.create_org_event(api_db, api_db.get(User, org.organizer_id),
                                 OrgEventIn(**FORM, layout="zones", mapId="arena", prices=prices))
    api_db.commit()
    try:
        body = c.get(f"/api/admin/events/{ev.id}").json()
        assert body["event"]["layout"] == "zones" and body["event"]["map"] == "arena"
        assert len(body["event"]["tiers"]) > 1 and all(t["group"] for t in body["event"]["tiers"])
    finally:
        drop_event(api_db, ev)


def test_public_still_404_for_pending(c, desk):
    ev = desk["event"]("xem-truoc-an", status="pending")
    assert c.get(f"/api/events/{ev.slug}").status_code == 404


@pytest.mark.parametrize("eid", ["0", "abc", "99999999", "2147483648"])
def test_preview_unknown_404(c, desk, eid):
    r = c.get(f"/api/admin/events/{eid}")
    assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}


def test_requires_admin(c, desk, api_db):
    ev = desk["event"]("xem-truoc-quyen", status="pending")
    buyer = make_customer(api_db, "khach-xem@x.vn")
    login(c, buyer.email)
    assert c.get(f"/api/admin/events/{ev.id}").status_code == 403


def test_approve_after_show_start_409(c, desk, api_db):
    ev = desk["event"]("duyet-qua-gio", status="pending", starts_at=datetime.now(timezone.utc) - timedelta(hours=1))
    r = c.post(f"/api/admin/events/{ev.id}/review", json={"decision": "approve"})
    assert r.status_code == 409 and r.json() == {"error": "Đã qua giờ diễn, không thể duyệt"}
    api_db.expire_all()
    assert api_db.get(Event, ev.id).status == "pending"
    r = c.post(f"/api/admin/events/{ev.id}/review", json={"decision": "reject", "reason": "Quá hạn"})
    assert r.status_code == 200  # trả lại vẫn được


def test_approve_future_still_ok(c, desk):
    ev = desk["event"]("duyet-dung-gio", status="pending")
    r = c.post(f"/api/admin/events/{ev.id}/review", json={"decision": "approve"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
