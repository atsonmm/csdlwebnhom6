"""GET /api/home (các khu trang chủ) và GET /api/maps/{id} (sơ đồ khớp dữ liệu JS cũ)"""
import json
from pathlib import Path

import pytest
from sqlalchemy import update

from app.models.catalog import HOME_SECTIONS, Event

HERE = Path(__file__).resolve().parent
CAT = json.loads((HERE.parent / "seed/catalog.json").read_text(encoding="utf-8"))
LEGACY_MAPS = json.loads((HERE / "fixtures/legacy_maps.json").read_text(encoding="utf-8"))


def sections(api) -> dict:
    r = api.get("/api/home")
    assert r.status_code == 200, r.text
    return r.json()["sections"]


def test_home_has_all_sections_in_position_order(api):
    s = sections(api)
    assert set(s) == set(HOME_SECTIONS)
    for name, cards in s.items():
        expected = [x["slug"] for x in sorted(CAT["homeSlots"], key=lambda x: x["position"]) if x["section"] == name]
        assert [c["slug"] for c in cards] == expected, name


def test_home_cards_carry_meta_and_card_fields(api):
    first = sections(api)["trending"][0]
    assert first["meta"] == {"rank": 1, "num": "text-mustard"}
    assert {"slug", "title", "start", "minPrice", "status", "categoryLabel"} <= set(first)


def test_home_skips_inactive_event(api, api_db):
    slug = sections(api)["hero"][0]["slug"]
    try:
        api_db.execute(update(Event).where(Event.slug == slug).values(active=False))
        api_db.commit()
        assert all(c["slug"] != slug for cards in sections(api).values() for c in cards)
    finally:
        api_db.execute(update(Event).where(Event.slug == slug).values(active=True))
        api_db.commit()


@pytest.mark.parametrize("legacy", LEGACY_MAPS, ids=lambda m: m["id"])
def test_map_matches_legacy(api, legacy):
    r = api.get(f"/api/maps/{legacy['id']}")
    assert r.status_code == 200
    assert r.json() == legacy


def test_unknown_map_404(api):
    r = api.get("/api/maps/khong-co")
    assert r.status_code == 404 and r.json() == {"error": "Sơ đồ không tồn tại"}
