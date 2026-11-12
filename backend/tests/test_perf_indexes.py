"""Task G2 — 2 chỉ mục mới (migration 0008) được planner dùng thật + công cụ đo EXPLAIN (ANALYZE, BUFFERS)"""
import json
import os

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import perf_bench, seed_large
from app.services import org_orders

INDEXES = ("ix_orders_buyer_trgm", "ix_orders_status_created")


@pytest.fixture(scope="module")
def big(engine, api_db):
    with Session(engine) as s:
        seed_large.generate(s, scale=0.2, seed=7)  # 20 000 đơn
        s.commit()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM ANALYZE orders"))  # gộp pending list của GIN như CSDL đã chạy lâu
    yield
    with Session(engine) as s:
        seed_large.clear(s)
        s.commit()


def _plan_nodes(plan: dict) -> list[tuple[str, str | None]]:
    out = [(plan["Node Type"], plan.get("Index Name"))]
    for child in plan.get("Plans", []):
        out += _plan_nodes(child)
    return out


def test_migration_0008_up_down(engine, schema):
    from alembic import command

    from app.config.database import make_engine
    from app.config.settings import settings
    from tests.test_migrations import _alembic_cfg

    sch = "mig0008"
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {sch}"))
    old = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-csearch_path={sch}"
    eng = make_engine(settings.test_database_url)
    cfg = _alembic_cfg()

    def present(conn):
        return {r[0] for r in conn.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname = :s"), {"s": sch})}

    try:
        command.upgrade(cfg, "0008")
        with eng.connect() as conn:
            assert set(INDEXES) <= present(conn)
            defs = dict(conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = :s"), {"s": sch}).all())
        assert "gin" in defs["ix_orders_buyer_trgm"] and "gin_trgm_ops" in defs["ix_orders_buyer_trgm"]
        assert "INCLUDE (event_id, total)" in defs["ix_orders_status_created"]
        command.downgrade(cfg, "0007")
        with eng.connect() as conn:
            assert not set(INDEXES) & present(conn)
        command.upgrade(cfg, "0008")
    finally:
        eng.dispose()
        if old is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = old
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {sch} CASCADE"))


def test_plans_use_new_indexes(big, engine):
    used = {}
    with engine.connect() as conn:
        for q in perf_bench.load_queries():
            plan = conn.execute(text("EXPLAIN (FORMAT JSON) " + q.sql), q.params).scalar()[0]["Plan"]
            used[q.name] = _plan_nodes(plan)
    assert ("Bitmap Index Scan", "ix_orders_buyer_trgm") in used["q1_order_search"], used["q1_order_search"]
    assert any(idx == "ix_orders_status_created" for _n, idx in used["q2_revenue_report"]), used["q2_revenue_report"]


@pytest.mark.parametrize("q", ["nguyen1", "TUAN.", "0309772", "Nguyễn Văn", "gmail.com", "Khách 4", "TL0000012", "tl00001", "%", "_", "'", "\\",
                               "x" * 500, "lon.ticketnhip"])
def test_search_results_unchanged(big, engine, q):
    """Biểu thức tìm mới (một chuỗi gộp, có chỉ mục trigram) cho đúng kết quả như cách cũ (ILIKE từng cột,
    mã đơn khớp tiền tố) với các từ khoá không vắt qua ranh giới hai cột"""
    with Session(engine) as s:
        params = org_orders.parse_list_params(q=q, event_id="", status="all", day_from="", day_to="",
                                              page="1", page_size="100")
        got = org_orders.list_orders(s, None, **params)
        w = org_orders._escape_like(params["q"])
        old = s.execute(text(r"""SELECT count(*) FROM orders o WHERE o.id ILIKE :p || '%' ESCAPE '\'
                                   OR o.buyer_name ILIKE '%' || :p || '%' ESCAPE '\'
                                   OR o.buyer_email ILIKE '%' || :p || '%' ESCAPE '\'
                                   OR o.buyer_phone ILIKE '%' || :p || '%' ESCAPE '\'"""), {"p": w}).scalar()
    assert got["total"] == old


def test_bench_measures_before_and_after(big, engine, tmp_path):
    rows = perf_bench.run(engine, runs=1, out_dir=tmp_path)
    assert {r["query"] for r in rows} == {"q1_order_search", "q2_revenue_report"}
    for r in rows:
        assert set(r) >= {"query", "phase", "median_ms", "min_ms", "max_ms", "nodes", "shared_hit", "shared_read"}
    assert {r["phase"] for r in rows} == {"before", "after"}
    assert len(list(tmp_path.glob("*.json"))) == 4  # kế hoạch đầy đủ trước/sau cho mỗi truy vấn
    with engine.connect() as conn:  # chỉ mục đã được tạo lại đúng như cũ
        names = {r[0] for r in conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'orders'"))}
    assert set(INDEXES) <= names
    before = next(r for r in rows if r["query"] == "q1_order_search" and r["phase"] == "before")
    assert "ix_orders_buyer_trgm" not in json.dumps(before["nodes"])
