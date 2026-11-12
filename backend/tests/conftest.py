"""Fixture dùng chung: engine trỏ tới CSDL test, TestClient của FastAPI."""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.database import get_db, make_engine
from app.main import app

BAD_DB_URL = "postgresql+psycopg://ticketnhip:sai@localhost:5432/ticketnhip"


def ensure_test_database(url: str) -> None:
    """Chặn chạy test (có DROP SCHEMA) trên CSDL không phải CSDL test"""
    from sqlalchemy.engine import make_url

    name = make_url(url).database or ""
    if not name.endswith("_test"):
        raise RuntimeError(f"TEST_DATABASE_URL phải trỏ tới CSDL có tên kết thúc bằng _test (đang là “{name}”)")


@pytest.fixture(scope="session")
def engine():
    eng = make_engine(settings.test_database_url)
    yield eng
    eng.dispose()


def _client_for(eng) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(engine):
    yield from _client_for(engine)


@pytest.fixture
def client_bad_db():
    eng = make_engine(BAD_DB_URL)
    yield from _client_for(eng)
    eng.dispose()


# ---------------------------------------------------------------------------
# Phiên CSDL cho test lược đồ: mỗi test chạy trong một transaction rồi rollback
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def schema(engine):
    """Dựng lược đồ test bằng chính migration Alembic (xoá sạch schema public trước)"""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    ensure_test_database(settings.test_database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    cfg.attributes["url"] = settings.test_database_url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
def db(engine, schema) -> Iterator[Session]:
    conn = engine.connect()
    trans = conn.begin()
    s = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield s
    finally:
        s.close()
        trans.rollback()
        conn.close()


def event_kwargs(category_id: str, **over) -> dict:
    base = dict(slug="su-kien-thu", title="Sự kiện thử", search_text="su kien thu", category_id=category_id,
                city="Hà Nội", venue="Nhà hát", address="1 Tràng Tiền", layout="list", description=[], notes=[])
    return {**base, **over}


@pytest.fixture
def make_category(db):
    from app.models.catalog import Category

    c = Category(id="nhac-song", label="Nhạc sống", dot="bg-tomato", sort_order=1)
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def make_map(db):
    from app.models.catalog import MapGroup, VenueMap

    m = VenueMap(id="arena", kind="zones", name="Sân khấu Arena", view_box="0 0 1000 680", decor={})
    db.add(m)
    db.flush()
    db.add(MapGroup(map_id=m.id, id="vip", label="VIP", color="#2a86a8", max_per_order=4, perks=""))
    db.flush()
    return m


@pytest.fixture
def make_event(db, make_category):
    from app.models.catalog import Event

    e = Event(**event_kwargs(make_category.id))
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def make_show_tier(db, make_event):
    """Sự kiện + 1 suất diễn + 1 hạng vé sức chứa 10"""
    from datetime import datetime, time, timezone

    from app.models.catalog import Show, TicketTier

    s = Show(event_id=make_event.id, id="20261115-1930",
             starts_at=datetime(2026, 11, 15, 12, 30, tzinfo=timezone.utc), end_time=time(22, 0))
    t = TicketTier(event_id=make_event.id, id="ve-1", name="Vé thường", price=300000, capacity=10, max_per_order=6)
    db.add_all([s, t])
    db.flush()
    return make_event, s, t


@pytest.fixture
def make_user(db):
    from app.models.users import User

    u = User(name="Khách", email="khach@x.vn", password_hash="h")
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def make_order(db, make_show_tier, make_user):
    from app.models.sales import Order

    e, s, t = make_show_tier
    o = Order(id="TN-AAAAAAA", user_id=make_user.id, event_id=e.id, show_id=s.id, subtotal=300000, discount=0,
              total=300000, method="qr", buyer_name="B", buyer_email="b@x.vn", buyer_phone="0912345678")
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def make_order_at(db, make_show_tier, make_user):
    """Tạo đơn đã thanh toán tại thời điểm cho trước: make_order_at(iso, total, items=[(tier_id, price, qty)], discount=0)"""
    from datetime import datetime
    from itertools import count

    from app.models.catalog import TicketTier
    from app.models.sales import Order, OrderItem

    e, s, _ = make_show_tier
    seq = count(1)

    def make(created_at: str, total: int, items: list[tuple[str, int, int]], discount: int = 0) -> Order:
        for tier_id, price, _qty in items:
            if db.get(TicketTier, (e.id, tier_id)) is None:
                db.add(TicketTier(event_id=e.id, id=tier_id, name=tier_id, price=price, capacity=100, max_per_order=6))
        db.flush()
        o = Order(id=f"TN-T{next(seq):06d}", user_id=make_user.id, event_id=e.id, show_id=s.id, subtotal=total + discount,
                  discount=discount, total=total, method="qr", buyer_name="B", buyer_email="b@x.vn",
                  buyer_phone="0912345678", created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")))
        db.add(o)
        db.flush()
        db.add_all([OrderItem(order_id=o.id, event_id=e.id, tier_id=t, price=p, qty=q) for t, p, q in items])
        db.flush()
        return o

    return make


# ---------------------------------------------------------------------------
# API danh mục: CSDL test đã nạp catalog.json (một lần mỗi module test), dọn sạch khi xong
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def api_db(engine, schema):
    import json
    from pathlib import Path

    from app.seed import load_catalog, reset_all

    catalog = json.loads((Path(__file__).resolve().parent.parent / "seed/catalog.json").read_text(encoding="utf-8"))
    with Session(engine) as s:
        reset_all(s)
        load_catalog(s, catalog)
        s.commit()
        yield s
        s.rollback()
        reset_all(s)
        s.commit()


@pytest.fixture(scope="module")
def api(engine, api_db):
    def override() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# API tài khoản: client mới cho mỗi test (giữ cookie), dọn tài khoản thử khi xong
# ---------------------------------------------------------------------------
TEST_ACCOUNT_FILTER = "email LIKE '%@x.vn' OR phone LIKE '09123456%' OR email LIKE '%@phien.vn'"


@pytest.fixture
def auth_db(engine, schema):
    from sqlalchemy import text

    with Session(engine) as s:
        yield s
        s.rollback()
        s.execute(text(f"DELETE FROM users WHERE {TEST_ACCOUNT_FILTER}"))
        s.commit()


@pytest.fixture
def c(engine, auth_db):
    def override() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    previous = app.dependency_overrides.get(get_db)  # giữ override của fixture api (phạm vi module) nếu có
    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app)
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


# ---------------------------------------------------------------------------
# Tài khoản theo vai trò, đã đăng nhập trên client `c` (CSDL đã nạp catalog qua fixture api)
# ---------------------------------------------------------------------------
def _login_as(api_db, client, email: str, role: str, org_name: str | None = None):
    from tests.booking_helpers import login, make_customer

    from app.models.users import Organizer

    u = make_customer(api_db, email)
    u.role = role
    if org_name:
        api_db.add(Organizer(user_id=u.id, org_name=org_name, phone="0987654321"))
    api_db.commit()
    login(client, email)
    return u


@pytest.fixture
def logged_customer(api, api_db, c):
    return _login_as(api_db, c, "khach@x.vn", "customer")


@pytest.fixture
def logged_admin(api, api_db, c):
    return _login_as(api_db, c, "quantri@x.vn", "admin")


@pytest.fixture
def logged_organizer(api, api_db, c):
    return _login_as(api_db, c, "btc@x.vn", "organizer", org_name="Công ty Sự kiện Thử")
