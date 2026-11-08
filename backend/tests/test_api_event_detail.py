"""GET /api/events/{slug}: dữ liệu phải khớp với giao diện JS cũ (tests/fixtures/legacy_events.json)"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, Show, TicketTier
from app.models.sales import TierStock
from tests.api_helpers import drop_org_event, make_org_event

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LEGACY = json.loads((FIXTURES / "legacy_events.json").read_text(encoding="utf-8"))
FIELDS = ["slug", "title", "category", "categoryLabel", "marker", "city", "venue", "address", "layout", "map",
          "saleOpensAt", "start", "startTime", "endTime", "minPrice", "organizer", "description", "notes", "resaleCount"]
ZONES = next(e for e in LEGACY if e["layout"] == "zones")


def expected_status(legacy: dict) -> str:
    # JS cũ: "coming" chỉ còn hiệu lực trước giờ mở bán (đếm ngược xong là bán)
    if legacy["status"] == "coming" and datetime.fromisoformat(legacy["saleOpensAt"]) > datetime.now().astimezone():
        return "coming"
    return "on-sale"


@pytest.mark.parametrize("legacy", LEGACY, ids=lambda e: e["slug"])
def test_detail_matches_legacy_event(api, legacy):
    r = api.get(f"/api/events/{legacy['slug']}")
    assert r.status_code == 200
    body = r.json()
    assert {k: body[k] for k in FIELDS} == {k: legacy[k] for k in FIELDS}
    assert body["status"] == expected_status(legacy)
    assert [{k: v for k, v in s.items() if k != "closed"} for s in body["shows"]] == legacy["shows"]
    assert all(isinstance(s["closed"], bool) for s in body["shows"])
    assert [{k: t[k] for k in legacy["tiers"][0]} for t in body["tiers"]] == legacy["tiers"]


def test_remaining_is_first_show_capacity_minus_presold_and_sold(api, api_db):
    body = api.get(f"/api/events/{ZONES['slug']}").json()
    eid = api_db.scalar(select(Event.id).where(Event.slug == ZONES["slug"]))
    stock = {s.tier_id: s for s in api_db.scalars(select(TierStock).where(
        TierStock.event_id == eid, TierStock.show_id == ZONES["shows"][0]["id"]))}
    for t in body["tiers"]:
        s = stock[t["id"]]
        assert t["capacity"] == s.capacity
        assert t["remaining"] == s.capacity - s.presold - s.sold


def test_unknown_slug_404(api):
    r = api.get("/api/events/khong-co")
    assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}


def test_inactive_event_is_hidden(api, api_db):
    slug = LEGACY[0]["slug"]
    try:
        api_db.execute(update(Event).where(Event.slug == slug).values(active=False))
        api_db.commit()
        assert api.get(f"/api/events/{slug}").status_code == 404
        assert all(r["slug"] != slug for e in LEGACY[1:3] for r in api.get(f"/api/events/{e['slug']}").json()["related"])
    finally:
        api_db.execute(update(Event).where(Event.slug == slug).values(active=True))
        api_db.commit()


def test_inactive_tier_and_show_are_hidden(api, api_db):
    ev = next(e for e in LEGACY if len(e["shows"]) >= 2)
    eid = api_db.scalar(select(Event.id).where(Event.slug == ev["slug"]))
    show_id, tier_id = ev["shows"][0]["id"], ev["tiers"][0]["id"]
    try:
        api_db.execute(update(Show).where(Show.event_id == eid, Show.id == show_id).values(active=False))
        api_db.execute(update(TicketTier).where(TicketTier.event_id == eid, TicketTier.id == tier_id).values(active=False))
        api_db.commit()
        body = api.get(f"/api/events/{ev['slug']}").json()
        assert show_id not in [s["id"] for s in body["shows"]]
        assert tier_id not in [t["id"] for t in body["tiers"]]
        assert body["start"] == ev["shows"][1]["start"]
    finally:
        api_db.execute(update(Show).where(Show.event_id == eid).values(active=True))
        api_db.execute(update(TicketTier).where(TicketTier.event_id == eid).values(active=True))
        api_db.commit()


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_unapproved_org_events_are_hidden(api, api_db, status):
    ev = make_org_event(api_db, slug=f"btc-{status}", status=status)
    try:
        r = api.get(f"/api/events/btc-{status}")
        assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}
    finally:
        drop_org_event(api_db, ev)


def test_approved_org_event_uses_organizer_profile(api, api_db):
    ev = make_org_event(api_db, slug="btc-da-duyet", status="approved", org_description=None,
                        starts_at=datetime(2026, 12, 20, 12, 30, tzinfo=timezone.utc))
    try:
        body = api.get("/api/events/btc-da-duyet").json()
        assert body["organizer"] == {"name": "Đơn vị btc-da-duyet", "bio": "Ban tổ chức trên TicketNhịp."}
        assert body["status"] == "on-sale" and body["start"] == "2026-12-20T19:30:00+07:00"
    finally:
        drop_org_event(api_db, ev)


def test_related_has_up_to_4_active_others(api):
    rel = api.get(f"/api/events/{LEGACY[0]['slug']}").json()["related"]
    assert 1 <= len(rel) <= 4
    assert all(r["slug"] != LEGACY[0]["slug"] for r in rel)
    assert set(rel[0]) >= {"slug", "title", "start", "minPrice", "status", "categoryLabel"}
