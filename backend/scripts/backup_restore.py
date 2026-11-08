"""Sao lưu / khôi phục CSDL PostgreSQL của TicketNhịp bằng pg_dump / pg_restore + đối chiếu số dòng.

    cd backend
    # sao lưu (định dạng custom -Fc, nén) + ghi kèm file đếm dòng <file>.counts.json
    .venv/Scripts/python.exe scripts/backup_restore.py backup  --database-url postgresql+psycopg://ticketnhip:ticketnhip@localhost/ticketnhip
    # khôi phục vào một CSDL ĐÃ TẠO SẴN (nên rỗng), rồi so số dòng với lúc sao lưu
    .venv/Scripts/python.exe scripts/backup_restore.py restore --file ../.data/backups/ticketnhip_20261108-1030.dump \
        --database-url postgresql+psycopg://ticketnhip:ticketnhip@localhost/ticketnhip_restore
    # chỉ so số dòng của một CSDL với file đếm
    .venv/Scripts/python.exe scripts/backup_restore.py verify --file <dump> --database-url <url>

Bản sao lưu nằm trong .data/backups/ (đã gitignore — không đưa dữ liệu lên GitHub).
pg_dump / pg_restore lấy từ PG_BIN (mặc định C:/Program Files/PostgreSQL/18/bin, nếu không có thì tìm trên PATH).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / ".data" / "backups"


def _tool(name: str) -> str:
    folder = Path(os.environ.get("PG_BIN", "C:/Program Files/PostgreSQL/18/bin"))
    exe = folder / (name + (".exe" if os.name == "nt" else ""))
    if exe.exists():
        return str(exe)
    found = shutil.which(name)
    if not found:
        sys.exit(f"Không tìm thấy {name} — đặt biến PG_BIN tới thư mục bin của PostgreSQL")
    return found


def _conn_args(url: str) -> tuple[list[str], dict]:
    u = make_url(url)
    env = os.environ | ({"PGPASSWORD": u.password} if u.password else {})
    return ["-h", u.host or "localhost", "-p", str(u.port or 5432), "-U", u.username or "postgres", "-d", u.database], env


def row_counts(url: str) -> dict[str, int]:
    """count(*) THẬT của mọi bảng thường trong schema public (kể cả alembic_version)"""
    eng = create_engine(url)
    with eng.connect() as conn:
        tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")).scalars().all()
        out = {t: int(conn.execute(text(f'SELECT count(*) FROM public."{t}"')).scalar()) for t in tables}
        out["_alembic_version"] = conn.execute(text("SELECT version_num FROM alembic_version")).scalar() if "alembic_version" in tables else None
    eng.dispose()
    return out


def backup(url: str, out: Path | None) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = make_url(url).database
    out = out or BACKUP_DIR / f"{name}_{datetime.now():%Y%m%d-%H%M%S}.dump"
    args, env = _conn_args(url)
    counts = row_counts(url)  # đếm NGAY trước khi dump (không ai ghi trong lúc này)
    t0 = time.perf_counter()
    subprocess.run([_tool("pg_dump"), *args, "-Fc", "--no-owner", "--no-privileges", "-f", str(out)], env=env, check=True)
    meta = {"database": name, "createdAt": datetime.now().isoformat(timespec="seconds"),
            "seconds": round(time.perf_counter() - t0, 2), "bytes": out.stat().st_size, "counts": counts}
    out.with_suffix(".counts.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã sao lưu {name} → {out} ({meta['bytes'] / 1e6:.1f} MB, {meta['seconds']}s, {sum(v for k, v in counts.items() if k != '_alembic_version')} dòng)")
    return out


def verify(url: str, dump: Path) -> bool:
    expected = json.loads(dump.with_suffix(".counts.json").read_text(encoding="utf-8"))["counts"]
    actual = row_counts(url)
    keys = sorted(set(expected) | set(actual))
    ok = True
    print(f"{'Bảng':<22}{'Lúc sao lưu':>14}{'Sau khôi phục':>16}")
    for k in keys:
        same = expected.get(k) == actual.get(k)
        ok &= same
        print(f"{k:<22}{str(expected.get(k)):>14}{str(actual.get(k)):>16}{'' if same else '   ← KHÁC'}")
    print("KẾT QUẢ:", "KHỚP — mọi bảng giữ nguyên số dòng" if ok else "KHÔNG KHỚP")
    return ok


def restore(url: str, dump: Path) -> bool:
    args, env = _conn_args(url)
    t0 = time.perf_counter()
    # --clean --if-exists: chạy lại được trên CSDL đích đã có dữ liệu cũ; --exit-on-error: lỗi là dừng, không im lặng
    subprocess.run([_tool("pg_restore"), *args, "--clean", "--if-exists", "--no-owner", "--no-privileges",
                    "--exit-on-error", str(dump)], env=env, check=True)
    print(f"Đã khôi phục {dump.name} → {make_url(url).database} trong {time.perf_counter() - t0:.1f}s")
    return verify(url, dump)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sao lưu / khôi phục CSDL TicketNhịp (pg_dump / pg_restore)")
    ap.add_argument("action", choices=["backup", "restore", "verify"])
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--file", type=Path)
    a = ap.parse_args()
    if a.action == "backup":
        backup(a.database_url, a.file)
        return
    if a.file is None:
        sys.exit("Cần --file <bản .dump>")
    ok = restore(a.database_url, a.file) if a.action == "restore" else verify(a.database_url, a.file)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
