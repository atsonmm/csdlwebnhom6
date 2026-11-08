"""Nâng CSDL dev lên head, ghi số dòng / trạng thái trước-sau → database/docs/migration-0006-proof.md (chạy trong backend/)"""
import pathlib
import platform
import subprocess
import sys
import time
from datetime import datetime

from sqlalchemy import create_engine, text

from app.config.settings import settings
from app.utils.timefmt import VN

TABLES = ("users", "organizers", "events", "shows", "ticket_tiers", "tier_stock", "seat_holds", "orders", "order_items", "tickets")
url = settings.database_url
engine = create_engine(url)


def snapshot() -> dict:
    with engine.connect() as c:
        return {
            "version": c.execute(text("SELECT version_num FROM alembic_version")).scalar(),
            "counts": {t: c.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in TABLES},
            "events": c.execute(text("SELECT status, count(*) FROM events GROUP BY status ORDER BY 1")).all(),
            "orders": c.execute(text("SELECT status, count(*) FROM orders GROUP BY status ORDER BY 1")).all(),
            "pg": c.execute(text("SHOW server_version")).scalar(),
            "db": c.execute(text("SELECT current_database()")).scalar(),
        }


before = snapshot()
t0 = time.perf_counter()
run = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True, encoding="utf-8")
elapsed = time.perf_counter() - t0
print(run.stdout, run.stderr)
if run.returncode != 0:
    sys.exit(f"alembic upgrade failed ({run.returncode})")
after = snapshot()

with engine.connect() as c:
    cols = c.execute(text("SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns "
                          "WHERE table_schema = current_schema() AND ((table_name = 'events' AND column_name IN "
                          "('cancel_reason','cancelled_at','cancelled_by')) OR (table_name = 'orders' AND column_name = 'refunded_at')) "
                          "ORDER BY 1, 2")).all()
    checks = c.execute(text("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname IN "
                            "('ck_events_status','ck_events_cancelled_by','ck_events_cancel_fields','ck_orders_refunded_at') ORDER BY 1")).all()
    nulls = c.execute(text("SELECT (SELECT count(*) FROM events WHERE cancel_reason IS NOT NULL OR cancelled_at IS NOT NULL "
                           "OR cancelled_by IS NOT NULL), (SELECT count(*) FROM orders WHERE refunded_at IS NOT NULL)")).one()

ok = before["counts"] == after["counts"] and before["events"] == after["events"] and before["orders"] == after["orders"]
now = datetime.now(VN).strftime("%Y-%m-%d %H:%M:%S %z")
L = [
    "# Biên bản chạy migration 0006 trên CSDL dev (đã có dữ liệu)",
    "",
    "Minh chứng học phần mục III.6. Mô tả thay đổi, kiểm tra dữ liệu cũ và phương án hạ phiên bản: [migration-0006.md](migration-0006.md).",
    "",
    f"- Thời điểm: {now}",
    f"- CSDL: `{before['db']}` · PostgreSQL {before['pg']} · {platform.system()} {platform.release()}",
    f"- Lệnh: `cd backend && .venv/Scripts/python.exe -m alembic upgrade head` (sinh bởi script ghi biên bản, chạy {elapsed:.2f} s)",
    f"- Phiên bản: `{before['version']}` → `{after['version']}`",
    f"- Kết luận: **{'số dòng và phân bố trạng thái KHÔNG đổi' if ok else 'CÓ KHÁC BIỆT — xem bảng'}**",
    "",
    "## Số dòng trước / sau",
    "",
    "| Bảng | Trước | Sau |",
    "|---|---:|---:|",
    *[f"| `{t}` | {before['counts'][t]:,} | {after['counts'][t]:,} |".replace(",", ".") for t in TABLES],
    "",
    "## Trạng thái sự kiện / đơn trước → sau",
    "",
    "| Bảng | Trạng thái | Trước | Sau |",
    "|---|---|---:|---:|",
    *[f"| events | `{s}` | {n} | {dict(after['events']).get(s, 0)} |" for s, n in before["events"]],
    *[f"| orders | `{s}` | {n} | {dict(after['orders']).get(s, 0)} |" for s, n in before["orders"]],
    "",
    "## Cột mới (đều cho phép NULL, dữ liệu cũ để NULL)",
    "",
    "| Bảng | Cột | Kiểu | NULL |",
    "|---|---|---|---|",
    *[f"| {t} | `{col}` | {dt} | {nl} |" for t, col, dt, nl in cols],
    "",
    f"Dòng cũ có giá trị ở cột mới: events = {nulls[0]}, orders = {nulls[1]} (mong đợi 0, 0).",
    "",
    "## Ràng buộc sau nâng cấp",
    "",
    *[f"- `{n}`: `{d}`" for n, d in checks],
    "",
    "## Đầu ra Alembic",
    "",
    "```",
    (run.stdout + run.stderr).strip() or "(không có)",
    "```",
    "",
]
out = pathlib.Path("../database/docs/migration-0006-proof.md")
out.write_text("\n".join(L), encoding="utf-8")
print("written", out, "ok" if ok else "DIFF")
