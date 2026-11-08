from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.config.database import Base


def test_models_match_migrations(engine, schema):
    """Model và migration phải khớp nhau, để `alembic revision --autogenerate` sau này
    không sinh ra thay đổi ngoài ý muốn (vd. xoá chú thích bảng)"""
    import app.models  # noqa: F401

    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert diff == []


# ---------------------------------------------------------------------------
# Migration 0006 trên CSDL ĐÃ CÓ DỮ LIỆU (học phần: thay đổi schema có quản lý phiên bản, kiểm tra dữ liệu cũ)
# Chạy trong một schema riêng (search_path qua PGOPTIONS) để không đụng lược đồ test dùng chung.
# ---------------------------------------------------------------------------
MIG_SCHEMA = "mig0006"
COUNTED = ("events", "shows", "ticket_tiers", "tier_stock", "orders", "order_items", "tickets", "users")


def _alembic_cfg():
    from pathlib import Path

    from alembic.config import Config

    from app.config.settings import settings

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    cfg.attributes["url"] = settings.test_database_url
    cfg.attributes["configure_logger"] = False
    return cfg


def _counts(conn) -> dict[str, int]:
    from sqlalchemy import text

    return {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in COUNTED}


def _populate_0005(eng) -> None:
    """Nạp catalog + một khách + đơn đã trả / đã hoàn bằng SQL thuần (lược đồ đang ở 0005)"""
    import json
    from pathlib import Path

    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from app.seed import load_catalog

    catalog = json.loads((Path(__file__).resolve().parent.parent / "seed/catalog.json").read_text(encoding="utf-8"))
    with Session(eng) as s:
        load_catalog(s, catalog)
        uid = s.execute(text("INSERT INTO users (name, email, password_hash) VALUES ('Khách cũ', 'cu@x.vn', 'h') RETURNING id")).scalar()
        eid, sid, tid, price = s.execute(text(
            "SELECT t.event_id, sh.id, t.id, t.price FROM ticket_tiers t JOIN shows sh ON sh.event_id = t.event_id "
            "JOIN events e ON e.id = t.event_id WHERE e.layout = 'list' ORDER BY t.event_id, t.id LIMIT 1")).one()
        for oid, status in (("TNMIG0001", "paid"), ("TNMIG0002", "refunded")):
            s.execute(text("INSERT INTO orders (id, user_id, event_id, show_id, subtotal, discount, total, method, buyer_name, "
                           "buyer_email, buyer_phone, status) VALUES (:o, :u, :e, :s, :p, 0, :p, 'qr', 'Khách cũ', 'cu@x.vn', "
                           "'0912345678', :st)"), {"o": oid, "u": uid, "e": eid, "s": sid, "p": price, "st": status})
            s.execute(text("INSERT INTO order_items (order_id, tier_id, event_id, price, qty) VALUES (:o, :t, :e, :p, 1)"),
                      {"o": oid, "t": tid, "e": eid, "p": price})
            s.execute(text("INSERT INTO tickets (code, order_id, event_id, tier_id, price) VALUES (:c, :o, :e, :t, :p)"),
                      {"c": oid[-4:] + "-MIG0", "o": oid, "e": eid, "t": tid, "p": price})
        s.commit()


def test_0006_upgrade_on_populated_db(engine, schema):
    import os

    import pytest
    from alembic import command
    from sqlalchemy import text

    from app.config.settings import settings
    from app.config.database import make_engine

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {MIG_SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {MIG_SCHEMA}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={MIG_SCHEMA}"  # mọi kết nối MỚI dưới đây làm việc trong schema riêng
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    try:
        command.upgrade(cfg, "0005")
        _populate_0005(eng)
        with eng.connect() as conn:
            assert conn.execute(text("SELECT current_schema()")).scalar() == MIG_SCHEMA
            before = _counts(conn)
            statuses = conn.execute(text("SELECT status, count(*) FROM events GROUP BY status ORDER BY 1")).all()
        assert before["events"] > 0 and before["orders"] == 2

        command.upgrade(cfg, "0006")
        with eng.connect() as conn:
            assert _counts(conn) == before  # không mất / thêm dòng nào
            assert conn.execute(text("SELECT status, count(*) FROM events GROUP BY status ORDER BY 1")).all() == statuses
            assert conn.execute(text("SELECT count(*) FROM events WHERE cancel_reason IS NOT NULL OR cancelled_at IS NOT NULL "
                                     "OR cancelled_by IS NOT NULL")).scalar() == 0
            assert conn.execute(text("SELECT count(*) FROM orders WHERE refunded_at IS NOT NULL")).scalar() == 0
            # ràng buộc mới có hiệu lực trên dữ liệu cũ
            with pytest.raises(Exception):
                with conn.begin():
                    conn.execute(text("UPDATE events SET status = 'cancelled' WHERE id = (SELECT min(id) FROM events)"))

        command.downgrade(cfg, "0005")  # chưa có sự kiện bị huỷ → hạ được
        command.upgrade(cfg, "0006")
        with eng.begin() as conn:
            conn.execute(text("UPDATE events SET status = 'cancelled', cancel_reason = 'Thử', cancelled_at = now(), "
                              "cancelled_by = 'organizer' WHERE id = (SELECT min(id) FROM events)"))
        with pytest.raises(Exception, match="cancelled"):
            command.downgrade(cfg, "0005")  # có sự kiện đã huỷ → dừng, không xoá dữ liệu âm thầm
        with eng.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM events WHERE status = 'cancelled'")).scalar() == 1
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0006"
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {MIG_SCHEMA} CASCADE"))


# ---------------------------------------------------------------------------
# Migration 0007 (bảng withdrawals) trên CSDL ĐÃ CÓ DỮ LIỆU: bảng mới rỗng, bảng cũ không đổi số dòng;
# hạ phiên bản bị chặn khi đã có yêu cầu rút tiền (không xoá dữ liệu tiền âm thầm).
# ---------------------------------------------------------------------------
def test_0007_upgrade_on_populated_db(engine, schema):
    import os

    import pytest
    from alembic import command
    from sqlalchemy import text

    from app.config.settings import settings
    from app.config.database import make_engine

    sch = "mig0007"
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {sch}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={sch}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    try:
        command.upgrade(cfg, "0006")
        _populate_0005(eng)  # dữ liệu kiểu cũ vẫn hợp lệ ở 0006
        with eng.connect() as conn:
            assert conn.execute(text("SELECT current_schema()")).scalar() == sch
            before = _counts(conn)
        assert before["events"] > 0 and before["orders"] == 2

        command.upgrade(cfg, "0007")
        with eng.connect() as conn:
            assert _counts(conn) == before
            assert conn.execute(text("SELECT count(*) FROM withdrawals")).scalar() == 0
            assert conn.execute(text("SELECT obj_description('withdrawals'::regclass)")).scalar()  # có chú thích bảng

        command.downgrade(cfg, "0006")  # bảng rỗng → hạ được
        with eng.connect() as conn:
            assert conn.execute(text("SELECT to_regclass('withdrawals')")).scalar() is None
        command.upgrade(cfg, "0007")
        with eng.begin() as conn:
            conn.execute(text("INSERT INTO organizers (user_id, org_name, phone) SELECT id, 'BTC cũ', '0912345678' "
                              "FROM users WHERE email = 'cu@x.vn'"))
            conn.execute(text("INSERT INTO withdrawals (organizer_id, amount, bank_name, account_no, account_name) "
                              "SELECT id, 50000, 'ACB', '123456', 'A' FROM users WHERE email = 'cu@x.vn'"))
        with pytest.raises(Exception, match="withdrawals"):
            command.downgrade(cfg, "0006")
        with eng.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM withdrawals")).scalar() == 1
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0007"
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))


def test_withdrawals_constraints(engine, schema):
    """Ràng buộc CSDL của withdrawals: số tiền > 0, trạng thái hợp lệ, pending ⇔ chưa xử lý, từ chối phải có lý do"""
    import pytest
    from sqlalchemy import text

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            uid = conn.execute(text("INSERT INTO users (name, email, password_hash, role) VALUES "
                                    "('BTC', 'rang-buoc-rut@x.vn', 'h', 'organizer') RETURNING id")).scalar()
            conn.execute(text("INSERT INTO organizers (user_id, org_name, phone) VALUES (:u, 'BTC', '0912345678')"),
                         {"u": uid})
            base = "INSERT INTO withdrawals (organizer_id, amount, bank_name, account_no, account_name{extra}) " \
                   "VALUES (:u, {amount}, 'ACB', '123456', 'A'{vals})"
            bad = [
                base.format(extra="", amount="0", vals=""),
                base.format(extra=", status", amount="50000", vals=", 'done'"),
                base.format(extra=", status", amount="50000", vals=", 'paid'"),  # paid mà chưa có processed_at
                base.format(extra=", processed_at", amount="50000", vals=", now()"),  # pending mà đã xử lý
                base.format(extra=", status, processed_at", amount="50000", vals=", 'rejected', now()"),  # thiếu lý do
            ]
            for sql in bad:
                sp = conn.begin_nested()
                with pytest.raises(Exception):
                    conn.execute(text(sql), {"u": uid})
                sp.rollback()
            conn.execute(text(base.format(extra=", status, processed_at, note", amount="50000",
                                          vals=", 'rejected', now(), 'Sai số tài khoản'")), {"u": uid})
        finally:
            trans.rollback()
