"""GET /api/events: danh sách & tìm kiếm không dấu"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import update

from app.models.catalog import Event
from app.utils.textnorm import normalize_vi
from tests.api_helpers import drop_org_event, make_org_event


def events(api, query: str = "") -> list[dict]:
    r = api.get(f"/api/events{query}")
    assert r.status_code == 200, r.text
    return r.json()["events"]


def test_default_lists_all_public_events_sorted_by_start(api):
    ev = events(api)
    assert len(ev) == 41
    assert [e["start"] for e in ev] == sorted(e["start"] for e in ev)
    assert all(e["start"].endswith("+07:00") for e in ev)


def test_normalize_vi_matches_js():
    # Kết quả của normalizeVi trong src/lib/utils.js với cùng đầu vào
    assert normalize_vi("Đêm Nhạc  Đà Lạt") == "dem nhac  da lat"
    assert normalize_vi("  Hà Nội ") == "ha noi"


@pytest.mark.parametrize("q", ["da lat", "dem nhac", "Đêm Nhạc", "HA NOI"])
def test_accent_insensitive_search(api, q):
    found = events(api, f"?q={q}")
    assert found, f"không tìm thấy gì cho {q!r}"
    words = normalize_vi(q).split()
    for e in found:
        text = normalize_vi(f"{e['title']} {e['city']} {e['venue']} {e['categoryLabel']}")
        assert all(w in text for w in words)


def test_search_without_match_returns_empty_list(api):
    assert events(api, "?q=khongtontaiđâu") == []


def test_filter_by_category_and_city(api):
    found = events(api, "?category=san-khau&city=TP.HCM")
    assert found and all(e["category"] == "san-khau" and e["city"] == "TP.HCM" for e in found)


def test_limit(api):
    assert len(events(api, "?limit=5")) == 5


@pytest.mark.parametrize("bad", ["?limit=0", "?limit=abc", "?limit=201", "?sort=gia"])
def test_bad_query_returns_400(api, bad):
    r = api.get(f"/api/events{bad}")
    assert r.status_code == 400 and r.json() == {"error": "Dữ liệu gửi lên không hợp lệ"}


def test_inactive_and_unapproved_events_excluded(api, api_db):
    slug = events(api)[0]["slug"]
    pending = make_org_event(api_db, slug="btc-cho-duyet", status="pending")
    try:
        api_db.execute(update(Event).where(Event.slug == slug).values(active=False))
        api_db.commit()
        slugs = {e["slug"] for e in events(api, "?limit=200")}
        assert slug not in slugs and "btc-cho-duyet" not in slugs
    finally:
        api_db.execute(update(Event).where(Event.slug == slug).values(active=True))
        api_db.commit()
        drop_org_event(api_db, pending)


def test_organizer_events_newest_reviewed_first(api, api_db):
    old = make_org_event(api_db, slug="btc-cu", reviewed_at=datetime(2026, 11, 1, tzinfo=timezone.utc))
    new = make_org_event(api_db, slug="btc-moi", reviewed_at=datetime(2026, 11, 5, tzinfo=timezone.utc))
    try:
        found = events(api, "?organizer=1&sort=reviewed")
        assert [e["slug"] for e in found] == ["btc-moi", "btc-cu"]
    finally:
        drop_org_event(api_db, new)
        drop_org_event(api_db, old)


@pytest.mark.parametrize("q", ["%", "_", "\\"])
def test_like_wildcards_are_literal(api, q):
    assert events(api, f"?q={q}") == []
