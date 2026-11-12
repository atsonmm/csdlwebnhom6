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


# ---------------------------------------------------------------------------
# Migration 0011 (gán mã tỉnh cho sự kiện cũ) trên CSDL ĐÃ CÓ DỮ LIỆU: khớp city với provinces.short_name
# (không phân biệt hoa thường; "Đà Lạt" → Lâm Đồng sau sáp nhập), street = địa chỉ cũ; không thêm / mất dòng nào.
# ---------------------------------------------------------------------------
def test_0011_backfill_locations_on_populated_db(engine, schema):
    import os

    from alembic import command
    from sqlalchemy import text

    from app.config.settings import settings
    from app.config.database import make_engine

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {MIG_SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {MIG_SCHEMA}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={MIG_SCHEMA}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    try:
        command.upgrade(cfg, "0010")
        _populate_0005(eng)  # catalog thật (city "Hà Nội", "TP.HCM", "Đà Lạt"…) + đơn hàng
        extra = [("thu-ha-noi-thuong", "Hà nội", "12 Phố Huế", False), ("thu-paris", "Paris", "Rue X", False),
                 ("thu-online", "Online", "", True), ("thu-dia-chi-dai", "Huế", "x" * 120, False)]
        with eng.begin() as conn:
            for slug, city, address, online in extra:
                conn.execute(text("INSERT INTO events (slug, title, search_text, category_id, city, venue, address, layout, "
                                  "description, notes, is_online) VALUES (:s, :t, :q, (SELECT min(id) FROM categories), "
                                  ":c, 'Nơi thử', :a, 'list', '{}', '{}', :o)"),
                             {"s": slug, "t": slug, "q": slug, "c": city, "a": address, "o": online})
            before = _counts(conn)
            cities = dict(conn.execute(text("SELECT slug, city FROM events")).all())

        command.upgrade(cfg, "0011")
        with eng.connect() as conn:
            assert _counts(conn) == before
            rows = {r.slug: r for r in conn.execute(text(
                "SELECT e.slug, e.city, e.address, e.street, e.province_code, e.ward_code, p.short_name "
                "FROM events e LEFT JOIN provinces p ON p.code = e.province_code"))}
            assert dict((s, r.city) for s, r in rows.items()) == cities  # city / address không đổi
            assert (rows["thu-ha-noi-thuong"].province_code, rows["thu-ha-noi-thuong"].street) == (1, "12 Phố Huế")
            assert rows["thu-paris"].province_code is None and rows["thu-paris"].street is None
            assert rows["thu-online"].province_code is None
            assert len(rows["thu-dia-chi-dai"].street) == 80 and rows["thu-dia-chi-dai"].province_code == 46
            catalog = [r for s, r in rows.items() if not s.startswith("thu-")]
            assert catalog and all(r.province_code is not None for r in catalog)  # mọi thành phố của catalog đều khớp
            dalat = [r for r in catalog if r.city == "Đà Lạt"]
            assert dalat and all(r.short_name == "Lâm Đồng" for r in dalat)
            assert all(r.ward_code is None for r in rows.values())
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {MIG_SCHEMA} CASCADE"))


def test_0016_resale_upgrade_on_populated_db(engine, schema):
    """0016 trên CSDL có dữ liệu: đơn cũ → kind primary, bỏ resale_count + slot 'resale'; hạ được khi chưa có tin,
    có tin bán lại thì dừng"""
    import os

    import pytest
    from alembic import command
    from sqlalchemy import text

    from app.config.database import make_engine
    from app.config.settings import settings

    sch = "mig0016"
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {sch}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={sch}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    try:
        command.upgrade(cfg, "0015")
        _populate_0005(eng)
        with eng.begin() as conn:
            conn.execute(text("UPDATE events SET resale_count = 7"))
            ev = conn.execute(text("SELECT event_id FROM home_slots LIMIT 1")).scalar()
            conn.execute(text("INSERT INTO home_slots (section, position, event_id, meta) "
                              "VALUES ('resale', 99, :e, '{}')"), {"e": ev})
            before = _counts(conn)
        assert before["orders"] == 2

        command.upgrade(cfg, "0016")
        with eng.connect() as conn:
            assert _counts(conn) == before
            assert conn.execute(text("SELECT count(*) FROM orders WHERE kind = 'primary'")).scalar() == 2
            assert conn.execute(text("SELECT count(*) FROM home_slots WHERE section = 'resale'")).scalar() == 0
            assert conn.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_schema = :s "
                                     "AND table_name = 'events' AND column_name = 'resale_count'"), {"s": sch}).scalar() == 0
            assert conn.execute(text("SELECT count(*) FROM tickets WHERE transferred_at IS NOT NULL")).scalar() == 0

        command.downgrade(cfg, "0015")  # chưa có tin bán lại → hạ được
        command.upgrade(cfg, "0016")
        with eng.begin() as conn:
            conn.execute(text(
                "INSERT INTO resale_listings (id, seller_id, event_id, show_id, tier_id, price) "
                "SELECT 'RSL000000001', o.user_id, o.event_id, o.show_id, t.tier_id, 100000 "
                "FROM orders o JOIN tickets t ON t.order_id = o.id LIMIT 1"))
        with pytest.raises(Exception, match="bán lại"):
            command.downgrade(cfg, "0015")
        with eng.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0016"
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))


def test_0017_refund_amount_backfill_on_populated_db(engine, schema):
    """0017 trên CSDL có dữ liệu: đơn đã hoàn có vé đã chuyển nhượng được tính lại refund_amount theo vé còn giữ;
    đơn khác giữ NULL (= hoàn đủ); CHECK chặn refund_amount ở đơn chưa hoàn; hạ được"""
    import os

    import pytest
    from alembic import command
    from sqlalchemy import text

    from app.config.database import make_engine
    from app.config.settings import settings

    sch = "mig0017"
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {sch}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={sch}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    try:
        command.upgrade(cfg, "0016")
        _populate_0005(eng)
        with eng.begin() as conn:
            ids = conn.execute(text("SELECT id FROM orders ORDER BY id")).scalars().all()
            partial, full = ids[0], ids[1]
            # thêm vé thứ hai cho đơn 'partial' (dữ liệu 0005 mỗi đơn một vé)
            conn.execute(text("INSERT INTO tickets (code, order_id, event_id, tier_id, price) "
                              "SELECT 'ZZZZ-ZZZ1', order_id, event_id, tier_id, price FROM tickets "
                              "WHERE order_id = :o LIMIT 1"), {"o": partial})
            conn.execute(text("UPDATE orders SET status = 'refunded', refunded_at = now() WHERE id IN (:a, :b)"),
                         {"a": partial, "b": full})
            # một vé của đơn 'partial' đã được bán lại trước khi sự kiện bị huỷ
            conn.execute(text("UPDATE tickets SET transferred_at = now() WHERE code = "
                              "(SELECT min(code) FROM tickets WHERE order_id = :o)"), {"o": partial})
            before = _counts(conn)
            expect = conn.execute(text(
                "SELECT (o.total * sum(t.price) FILTER (WHERE t.transferred_at IS NULL)) / sum(t.price) "
                "FROM orders o JOIN tickets t ON t.order_id = o.id WHERE o.id = :o GROUP BY o.total"),
                {"o": partial}).scalar()

        command.upgrade(cfg, "0017")
        with eng.connect() as conn:
            assert _counts(conn) == before
            got = dict(conn.execute(text("SELECT id, refund_amount FROM orders")).all())
            assert got[partial] == expect and got[partial] < conn.execute(
                text("SELECT total FROM orders WHERE id = :o"), {"o": partial}).scalar()
            assert got[full] is None  # không vé nào chuyển nhượng → NULL = hoàn đủ total
        with pytest.raises(Exception, match="ck_orders_refund_amount"):
            with eng.begin() as conn:
                conn.execute(text("UPDATE orders SET status = 'paid', refunded_at = NULL WHERE id = :o"), {"o": partial})

        command.downgrade(cfg, "0016")
        with eng.connect() as conn:
            assert _counts(conn) == before
            assert conn.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_schema = :s "
                                     "AND table_name = 'orders' AND column_name = 'refund_amount'"), {"s": sch}).scalar() == 0
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))


def test_0018_order_hold_on_populated_db(engine, schema):
    """0018 trên CSDL có dữ liệu: đơn cũ giữ nguyên; đơn 'pending' được phép thiếu thông tin người mua nhưng bắt buộc
    có expires_at; đơn 'paid' vẫn bắt buộc đủ thông tin; hạ phiên bản được khi không còn đơn pending / expired"""
    import os

    import pytest
    from alembic import command
    from sqlalchemy import text

    from app.config.database import make_engine
    from app.config.settings import settings

    sch = "mig0018"
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {sch}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={sch}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    insert = ("INSERT INTO orders (id, user_id, event_id, show_id, subtotal, discount, total, method, buyer_name, "
              "buyer_email, buyer_phone, status, expires_at) "
              "SELECT :id, user_id, event_id, show_id, subtotal, 0, subtotal, {method}, {buyer}, {buyer}, {buyer}, "
              ":status, {expires} FROM orders LIMIT 1")
    try:
        command.upgrade(cfg, "0017")
        _populate_0005(eng)
        with eng.begin() as conn:
            before = _counts(conn)
            snapshot = conn.execute(text("SELECT id, status, method, buyer_email FROM orders ORDER BY id")).all()

        command.upgrade(cfg, "0018")
        with eng.begin() as conn:
            assert _counts(conn) == before
            assert conn.execute(text("SELECT id, status, method, buyer_email FROM orders ORDER BY id")).all() == snapshot
            conn.execute(text(insert.format(method="NULL", buyer="NULL", expires="now() + interval '15 minutes'")),
                         {"id": "TNPEND0001", "status": "pending"})  # giữ chỗ: chưa có người mua / phương thức
        with pytest.raises(Exception, match="ck_orders_pending_expiry"):
            with eng.begin() as conn:
                conn.execute(text(insert.format(method="NULL", buyer="NULL", expires="NULL")),
                             {"id": "TNPEND0002", "status": "pending"})
        with pytest.raises(Exception, match="ck_orders_buyer_known"):
            with eng.begin() as conn:
                conn.execute(text(insert.format(method="NULL", buyer="NULL", expires="NULL")),
                             {"id": "TNPAID0001", "status": "paid"})
        with eng.begin() as conn:
            conn.execute(text(insert.format(method="NULL", buyer="NULL", expires="now() - interval '1 minute'")),
                         {"id": "TNEXP00001", "status": "expired"})  # hết hạn vẫn được phép thiếu thông tin
            conn.execute(text("DELETE FROM orders WHERE status IN ('pending', 'expired')"))

        command.downgrade(cfg, "0017")
        with eng.connect() as conn:
            assert _counts(conn) == before
            assert conn.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_schema = :s "
                                     "AND table_name = 'orders' AND column_name = 'expires_at'"), {"s": sch}).scalar() == 0
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))


def test_0019_checkout_questions_on_populated_db(engine, schema):
    """0019 trên CSDL có dữ liệu: dữ liệu cũ giữ nguyên, hai bảng mới dùng được, hạ phiên bản xoá sạch hai bảng"""
    import os

    from alembic import command
    from sqlalchemy import text

    from app.config.database import make_engine
    from app.config.settings import settings

    sch = "mig0019"
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {sch}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={sch}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    tables = "SELECT count(*) FROM information_schema.tables WHERE table_schema = :s AND table_name IN " \
             "('event_questions', 'order_answers')"
    try:
        command.upgrade(cfg, "0018")
        _populate_0005(eng)
        with eng.begin() as conn:
            before = _counts(conn)
            assert conn.execute(text(tables), {"s": sch}).scalar() == 0

        command.upgrade(cfg, "0019")
        with eng.begin() as conn:
            assert _counts(conn) == before
            assert conn.execute(text(tables), {"s": sch}).scalar() == 2
            ev, order = conn.execute(text("SELECT event_id, id FROM orders LIMIT 1")).one()
            conn.execute(text("INSERT INTO event_questions (event_id, id, kind, label, sort_order) "
                              "VALUES (:e, 'terms', 'consent', 'Đồng ý điều khoản?', 0)"), {"e": ev})
            conn.execute(text("INSERT INTO order_answers (order_id, event_id, question_id, value, label_snapshot) "
                              "VALUES (:o, :e, 'terms', 'true', 'Đồng ý điều khoản?')"), {"o": order, "e": ev})

        command.downgrade(cfg, "0018")
        with eng.connect() as conn:
            assert _counts(conn) == before
            assert conn.execute(text(tables), {"s": sch}).scalar() == 0
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))


def test_0020_multi_choice_kind_on_populated_db(engine, schema):
    """0020 trên CSDL có dữ liệu: câu hỏi / câu trả lời cũ giữ nguyên, nhận thêm loại 'multi'; hạ phiên bản xoá các câu 'multi'
    (và câu trả lời của chúng) rồi trả ràng buộc cũ"""
    import os

    import pytest
    from alembic import command
    from sqlalchemy import text

    from app.config.database import make_engine
    from app.config.settings import settings

    sch = "mig0020"
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {sch}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={sch}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()
    try:
        command.upgrade(cfg, "0019")
        _populate_0005(eng)
        with eng.begin() as conn:
            ev, order = conn.execute(text("SELECT event_id, id FROM orders LIMIT 1")).one()
            conn.execute(text("INSERT INTO event_questions (event_id, id, kind, label, sort_order) VALUES (:e, 'terms', 'consent', 'Đồng ý?', 0)"), {"e": ev})
            conn.execute(text("INSERT INTO order_answers (order_id, event_id, question_id, value, label_snapshot) VALUES (:o, :e, 'terms', 'true', 'Đồng ý?')"), {"o": order, "e": ev})
            before = _counts(conn)
        with pytest.raises(Exception, match="ck_event_questions_kind"):
            with eng.begin() as conn:
                conn.execute(text("INSERT INTO event_questions (event_id, id, kind, label, options) VALUES (:e, 'm', 'multi', 'x', '[\"a\",\"b\"]')"), {"e": ev})

        command.upgrade(cfg, "0020")
        with eng.begin() as conn:
            assert _counts(conn) == before
            assert conn.execute(text("SELECT count(*) FROM event_questions")).scalar() == 1  # câu cũ còn nguyên
            conn.execute(text("INSERT INTO event_questions (event_id, id, kind, label, options, sort_order) VALUES (:e, 'm', 'multi', 'Thích gì?', '[\"a\",\"b\"]', 1)"), {"e": ev})
            conn.execute(text("INSERT INTO order_answers (order_id, event_id, question_id, value, label_snapshot) VALUES (:o, :e, 'm', '[\"a\"]', 'Thích gì?')"), {"o": order, "e": ev})
        with pytest.raises(Exception, match="ck_event_questions_options"):
            with eng.begin() as conn:
                conn.execute(text("INSERT INTO event_questions (event_id, id, kind, label) VALUES (:e, 'm2', 'multi', 'thiếu lựa chọn')"), {"e": ev})

        command.downgrade(cfg, "0019")
        with eng.connect() as conn:
            assert _counts(conn) == before
            assert conn.execute(text("SELECT id FROM event_questions")).scalars().all() == ["terms"]
            assert conn.execute(text("SELECT question_id FROM order_answers")).scalars().all() == ["terms"]
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
