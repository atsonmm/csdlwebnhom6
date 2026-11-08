from sqlalchemy import text


def test_daily_revenue_uses_vietnam_day(db, make_order_at):
    make_order_at("2026-11-06T18:30:00Z", total=550000, items=[("ve-1", 600000, 1)], discount=50000)
    row = db.execute(text("select day, revenue, tickets from v_daily_revenue")).one()
    assert str(row.day) == "2026-11-07" and row.revenue == 550000 and row.tickets == 1


def test_daily_revenue_not_doubled_by_multiple_items(db, make_order_at):
    make_order_at("2026-11-06T03:00:00Z", total=900000, items=[("ve-1", 300000, 1), ("ve-2", 600000, 1)])
    row = db.execute(text("select revenue, tickets from v_daily_revenue")).one()
    assert row.revenue == 900000 and row.tickets == 2


def test_event_sales_per_tier(db, make_order_at):
    make_order_at("2026-11-06T03:00:00Z", total=900000, items=[("ve-1", 300000, 3)])
    make_order_at("2026-11-06T04:00:00Z", total=300000, items=[("ve-1", 300000, 1)])
    row = db.execute(text("select tier_id, sold, revenue from v_event_sales")).one()
    assert row.tier_id == "ve-1" and row.sold == 4 and row.revenue == 1200000


def test_every_table_has_comment(db):
    missing = db.execute(text("""select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind in ('r','v') and c.relname <> 'alembic_version'
        and obj_description(c.oid) is null order by 1""")).scalars().all()
    assert missing == []
