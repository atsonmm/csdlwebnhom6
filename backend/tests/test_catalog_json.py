"""Kiểm tra catalog.json xuất từ dữ liệu JS (backend/seed/export_catalog.mjs)"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # backend/
PROJECT = ROOT.parent                                   # ticketnhip/
CAT = json.loads((ROOT / "seed/catalog.json").read_text(encoding="utf-8"))


def test_every_event_has_show_and_tier():
    assert CAT["events"]
    assert all(e["shows"] and e["tiers"] for e in CAT["events"])


def test_slugs_unique_and_alias_merged():
    slugs = [e["slug"] for e in CAT["events"]]
    assert len(slugs) == len(set(slugs))
    assert "concert-dem-4-tinh-ha" not in slugs
    assert "concert-dem-4-hen-giua-tinh-ha" in slugs


def test_home_slots_point_to_existing_events():
    slugs = {e["slug"] for e in CAT["events"]}
    assert CAT["homeSlots"]
    assert all(s["slug"] in slugs for s in CAT["homeSlots"])


def test_show_ids_are_vietnam_local_time():
    ev = next(e for e in CAT["events"] if e["slug"] == "concert-dem-4-hen-giua-tinh-ha")
    s = ev["shows"][0]
    assert s["startsAt"].endswith("+07:00")
    assert s["id"] == s["startsAt"][:10].replace("-", "") + "-" + s["startsAt"][11:16].replace(":", "")


def test_zone_presold_within_capacity():
    for e in CAT["events"]:
        cap = {t["id"]: t["capacity"] for t in e["tiers"]}
        assert all(0 <= p["qty"] <= cap[p["tierId"]] for p in e["presold"])


def test_seat_events_reference_existing_seats():
    seats = {m["id"]: {s["id"] for s in m["seats"]} for m in CAT["maps"] if m["kind"] == "seats"}
    for e in CAT["events"]:
        if e["layout"] == "seats":
            assert e["presoldSeats"], e["slug"]
            assert all(p["seatId"] in seats[e["mapId"]] for p in e["presoldSeats"])


def test_export_refuses_wrong_timezone():
    r = subprocess.run(["node", "backend/seed/export_catalog.mjs", "--check-only"], cwd=PROJECT,
                       env={**os.environ, "TZ": "UTC"}, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1
    assert "TZ=Asia/Ho_Chi_Minh" in r.stderr
