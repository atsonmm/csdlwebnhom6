"""Task B3 — /api/admin/reports (toàn sàn + byOrganizer), /api/admin/organizers (số liệu), /api/admin/organizers/{id}/events"""
from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, Show, TicketTier
from app.models.sales import Order, TierStock
from app.services.manage import fee_of
from app.utils.timefmt import VN
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer

TODAY = datetime.now(VN).date()
DAY = TODAY - timedelta(days=2)


def at(day: date) -> datetime:
    return datetime.combine(day, time(10, 0), tzinfo=VN)


@pytest.fixture
def floor(c, logged_organizer, api_db, auth_db):
    reviewed = datetime.now(timezone.utc) - timedelta(days=10)
    mine = make_org_event(api_db, slug="bc-san-cua-toi", organizer_id=logged_organizer.id, reviewed_at=reviewed)
    pend = make_org_event(api_db, slug="bc-san-cho-duyet", organizer_id=logged_organizer.id, status="pending")
    other = make_org_event(api_db, slug="bc-san-btc-khac", reviewed_at=reviewed)
    platform = api_db.scalar(select(Event).where(Event.organizer_id.is_(None), Event.layout == "list",
                                                 Event.status == "approved").order_by(Event.id))
    p_show = api_db.scalar(select(Show.id).where(Show.event_id == platform.id, Show.active).order_by(Show.starts_at))
    p_tier = api_db.scalar(select(TicketTier.id).where(TicketTier.event_id == platform.id, TicketTier.active)
                           .order_by(TicketTier.sort_order))
    buyer = make_customer(api_db, "mua-bc-san@x.vn")
    o_mine = insert_order(api_db, buyer, mine.slug, mine._test_show_id, [("ve-1", 3)], created_at=at(DAY))
    o_other = insert_order(api_db, buyer, other.slug, other._test_show_id, [("ve-1", 1)], created_at=at(DAY))
    o_plat = insert_order(api_db, buyer, platform.slug, p_show, [(p_tier, 1)], created_at=at(DAY))
    admin = make_customer(api_db, "quantri-bc@x.vn")
    admin.role = "admin"
    api_db.commit()
    yield {"mine": mine, "pend": pend, "other": other, "platform": platform, "org": logged_organizer,
           "o_mine": o_mine, "o_other": o_other, "o_plat": o_plat, "admin": admin.email}
    api_db.rollback()
    api_db.execute(Order.__table__.delete().where(Order.id == o_plat.id))
    api_db.execute(update(TierStock).where(TierStock.event_id == platform.id, TierStock.show_id == p_show,
                                           TierStock.tier_id == p_tier).values(sold=TierStock.sold - 1))
    api_db.commit()
    for ev in (mine, pend):
        drop_event(api_db, ev)
    drop_org_event(api_db, other)


RANGE = {"from": DAY.isoformat(), "to": DAY.isoformat()}


def test_admin_report_totals_equal_sum_of_organizers(c, floor):
    login(c, floor["admin"])
    body = c.get("/api/admin/reports", params=RANGE).json()
    rows = {r["organizerId"]: r for r in body["byOrganizer"]}
    assert sum(r["revenue"] for r in body["byOrganizer"]) == body["totals"]["revenue"]
    assert sum(r["fee"] for r in body["byOrganizer"]) == body["totals"]["fee"]
    plat = rows[None]
    assert plat["orgName"] == "Sàn TicketNhịp" and plat["fee"] == 0 and plat["revenue"] >= floor["o_plat"].total
    assert body["totals"]["platformRevenue"] == plat["revenue"]
    me = rows[floor["org"].id]
    assert me["orgName"] == "Công ty Sự kiện Thử" and me["revenue"] == floor["o_mine"].total
    assert me["fee"] == fee_of(floor["o_mine"].total) and me["net"] == me["revenue"] - me["fee"]
    assert me["tickets"] == 3 and me["orders"] == 1
    assert body["byOrganizer"] == sorted(body["byOrganizer"], key=lambda r: -r["revenue"])


def test_admin_report_matches_org_report(c, floor):
    own = c.get("/api/organizer/reports", params=RANGE).json()  # c đang là BTC
    login(c, floor["admin"])
    adm = c.get("/api/admin/reports", params=RANGE | {"organizerId": floor["org"].id}).json()
    for k in ("range", "totals", "series", "byEvent", "byTier"):
        got = adm[k]
        if k == "totals":
            got = {kk: v for kk, v in got.items() if kk != "platformRevenue"}
        assert got == own[k], k


def test_admin_report_validation(c, floor):
    login(c, floor["admin"])
    r = c.get("/api/admin/reports", params={"organizerId": "x"})
    assert r.status_code == 400 and r.json() == {"error": "Mã ban tổ chức không hợp lệ"}
    assert c.get("/api/admin/reports", params={"groupBy": "year"}).status_code == 400


def test_organizers_list_counts(c, floor):
    login(c, floor["admin"])
    rows = {o["userId"]: o for o in c.get("/api/admin/organizers").json()["organizers"]}
    me = rows[floor["org"].id]
    assert (me["events"], me["live"], me["pending"]) == (2, 1, 1)
    assert me["revenue"] == floor["o_mine"].total and me["fee"] == fee_of(floor["o_mine"].total)
    assert rows[floor["other"].organizer_id]["revenue"] == floor["o_other"].total


def test_organizer_events(c, floor):
    login(c, floor["admin"])
    evs = c.get(f"/api/admin/organizers/{floor['org'].id}/events").json()["events"]
    assert {e["id"] for e in evs} == {floor["mine"].id, floor["pend"].id}
    mine = next(e for e in evs if e["id"] == floor["mine"].id)
    assert mine["revenue"] == floor["o_mine"].total and mine["phase"] == "on-sale"


@pytest.mark.parametrize("bad", ["999999", "abc", "99999999999"])
def test_organizer_events_404_unknown(c, floor, bad):
    login(c, floor["admin"])
    r = c.get(f"/api/admin/organizers/{bad}/events")
    assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy ban tổ chức"}


def test_requires_admin(c, logged_organizer):
    assert c.get("/api/admin/reports").status_code == 403
    assert c.get(f"/api/admin/organizers/{logged_organizer.id}/events").status_code == 403
