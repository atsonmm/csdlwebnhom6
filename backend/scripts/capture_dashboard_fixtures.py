"""Chụp dữ liệu dashboard Ban tổ chức cho test giao diện → src/test/fixtures/org-*.json

Chạy TRONG TIẾN TRÌNH (FastAPI TestClient) trên CSDL test — không cần bật server:
    cd backend && .venv/Scripts/python.exe scripts/capture_dashboard_fixtures.py
Dọn sạch CSDL test khi xong."""
import json
import sys
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config.settings import settings  # noqa: E402
from app.config.database import get_db, make_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.catalog import Event  # noqa: E402
from app.models.sales import Order  # noqa: E402
from app.seed import load_catalog, reset_all  # noqa: E402
from app.utils.timefmt import VN  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "test" / "fixtures"
CATALOG = Path(__file__).resolve().parents[1] / "seed" / "catalog.json"

if not settings.test_database_url.rsplit("/", 1)[-1].endswith("_test"):
    raise SystemExit("TEST_DATABASE_URL phải là CSDL _test")
engine = make_engine(settings.test_database_url)
engine.echo = False


def override() -> Iterator[Session]:
    with Session(engine) as s:
        yield s


app.dependency_overrides[get_db] = override


def save(name: str, data) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  ✓ {name}.json")


def ok(r):
    assert r.status_code < 300, r.text
    return r.json()


with Session(engine) as db:
    reset_all(db)
    load_catalog(db, json.loads(CATALOG.read_text(encoding="utf-8")))
    db.commit()
try:
    org, buyer = TestClient(app), TestClient(app)
    ok(org.post("/api/auth/register", json={"name": "BTC Fixture", "identifier": "btc@fixture.vn", "password": "matkhau123"}))
    ok(org.post("/api/organizer/register", json={"orgName": "Công ty Fixture", "phone": "0912000999", "description": ""}))
    day = (datetime.now(VN) + timedelta(days=30)).date()
    base = {"category": "nhac-song", "city": "Hà Nội", "venue": "Nhà hát Lớn", "address": "", "date": day.isoformat(),
            "startTime": "19:30", "endTime": "22:00", "description": "Sự kiện tạm để chụp dữ liệu dashboard.",
            "tiers": [{"name": "Vé thường", "price": 300000, "quantity": 100}, {"name": "VIP", "price": 900000, "quantity": 20}]}
    on_sale = ok(org.post("/api/organizer/events", json=base | {"title": "Đêm Nhạc Đang Bán"}))["event"]
    upcoming = ok(org.post("/api/organizer/events", json=base | {
        "title": "Đêm Nhạc Sắp Mở Bán", "saleStart": f"{(day - timedelta(days=3)).isoformat()}T10:00"}))["event"]
    pending = ok(org.post("/api/organizer/events", json=base | {"title": "Đêm Nhạc Chờ Duyệt"}))["event"]
    rejected = ok(org.post("/api/organizer/events", json=base | {"title": "Đêm Nhạc Bị Trả Lại"}))["event"]
    with Session(engine) as db:
        now = datetime.now(timezone.utc)
        db.execute(update(Event).where(Event.id.in_([on_sale["id"], upcoming["id"]]))
                   .values(status="approved", reviewed_at=now - timedelta(days=2)))
        db.execute(update(Event).where(Event.id == rejected["id"])
                   .values(status="rejected", reject_reason="Thiếu ảnh bìa và giấy phép biểu diễn.", reviewed_at=now))
        db.commit()
    ok(buyer.post("/api/auth/register", json={"name": "Lê Thu Hà", "identifier": "ha@fixture.vn", "password": "matkhau123"}))
    who = {"name": "Lê Thu Hà", "email": "ha@fixture.vn", "phone": "0900000003"}
    o1 = ok(buyer.post("/api/orders", json={"slug": on_sale["slug"], "items": [{"tierId": "ve-1", "qty": 2}], "method": "qr", "buyer": who}))
    o2 = ok(buyer.post("/api/orders", json={"slug": on_sale["slug"], "items": [{"tierId": "ve-2", "qty": 1}], "method": "card",
                                            "coupon": "NHIP50", "buyer": who}))
    with Session(engine) as db:  # rải đơn sang 2 ngày khác nhau (giờ VN)
        db.execute(update(Order).where(Order.id == o1["order"]["id"]).values(created_at=now - timedelta(days=1)))
        db.commit()
    save("org-me", ok(org.get("/api/organizer/me")))
    save("org-stats", ok(org.get("/api/organizer/stats")))
    save("org-event-detail", ok(org.get(f"/api/organizer/events/{on_sale['id']}")))
    print(f"  (sự kiện: đang bán #{on_sale['id']}, sắp mở bán #{upcoming['id']}, chờ duyệt #{pending['id']}, trả lại #{rejected['id']})")
finally:
    with Session(engine) as db:
        reset_all(db)
        db.commit()
    engine.dispose()
