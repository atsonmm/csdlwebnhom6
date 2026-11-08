"""Đo hiệu năng trước/sau khi có chỉ mục (Task G2): EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON).

Mỗi truy vấn trong backend/perf/*.sql có dòng đầu dạng `-- params: {...}` (tham số cố định, JSON) và dòng
`-- index: <tên chỉ mục>` (chỉ mục mà truy vấn đó cần). Quy trình (cùng một CSDL, cùng dữ liệu):
    1. đọc định nghĩa chỉ mục từ pg_indexes (CSDL phải ở migration ≥ 0008), DROP INDEX, VACUUM ANALYZE orders,
       chạy mỗi truy vấn N lần → "before";
    2. tạo lại chỉ mục bằng ĐÚNG định nghĩa đã đọc, VACUUM ANALYZE, chạy N lần → "after".
Trả về trung vị / min / max thời gian thực thi, các node của kế hoạch, shared hit/read; lưu kế hoạch đầy đủ (JSON).
"""
import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

PERF_DIR = Path(__file__).resolve().parent.parent / "perf"


@dataclass
class PerfQuery:
    name: str
    sql: str
    params: dict
    index: str


def load_queries(folder: Path = PERF_DIR) -> list[PerfQuery]:
    out = []
    for f in sorted(folder.glob("*.sql")):
        body = f.read_text(encoding="utf-8")
        params = json.loads(re.search(r"^-- params: (.*)$", body, re.M).group(1))
        index = re.search(r"^-- index: (\S+)$", body, re.M).group(1)
        sql = "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("--")).strip().rstrip(";")
        out.append(PerfQuery(f.stem, sql, params, index))
    return out


def _nodes(plan: dict) -> list[dict]:
    out = [{"node": plan["Node Type"], "index": plan.get("Index Name"), "relation": plan.get("Relation Name")}]
    for child in plan.get("Plans", []):
        out += _nodes(child)
    return out


def _measure(engine: Engine, q: PerfQuery, runs: int) -> tuple[list[float], dict]:
    times, last = [], None
    with engine.connect() as conn:
        for _ in range(runs):
            last = conn.execute(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + q.sql), q.params).scalar()[0]
            times.append(float(last["Execution Time"]))
        conn.rollback()
    return times, last


def _vacuum(engine: Engine) -> None:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM ANALYZE orders"))


def run(engine: Engine, *, runs: int = 5, out_dir: Path | None = None, queries: list[PerfQuery] | None = None) -> list[dict]:
    queries = queries or load_queries()
    names = sorted({q.index for q in queries})
    with engine.begin() as conn:
        defs = dict(conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE indexname = ANY(:n)"),
                                 {"n": names}).all())
    missing = set(names) - set(defs)
    if missing:
        raise RuntimeError(f"Thiếu chỉ mục {sorted(missing)} — nâng CSDL lên migration 0008 trước khi đo")
    rows: list[dict] = []
    try:
        with engine.begin() as conn:
            for n in names:
                conn.execute(text(f'DROP INDEX "{n}"'))
        rows += _phase(engine, queries, "before", runs, out_dir)
    finally:
        with engine.begin() as conn:  # luôn tạo lại, kể cả khi đo lỗi giữa chừng
            have = {r[0] for r in conn.execute(text("SELECT indexname FROM pg_indexes WHERE indexname = ANY(:n)"),
                                               {"n": names})}
            for n in names:
                if n not in have:
                    conn.execute(text(defs[n]))
    rows += _phase(engine, queries, "after", runs, out_dir)
    return rows


def _phase(engine: Engine, queries: list[PerfQuery], phase: str, runs: int, out_dir: Path | None) -> list[dict]:
    _vacuum(engine)
    rows = []
    for q in queries:
        times, plan = _measure(engine, q, runs)
        top = plan["Plan"]
        rows.append({"query": q.name, "phase": phase, "median_ms": round(statistics.median(times), 3),
                     "min_ms": round(min(times), 3), "max_ms": round(max(times), 3),
                     "nodes": _nodes(top), "shared_hit": top.get("Shared Hit Blocks", 0),
                     "shared_read": top.get("Shared Read Blocks", 0), "planning_ms": plan.get("Planning Time")})
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{q.name}_{phase}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2),
                                                            encoding="utf-8")
    return rows


def to_markdown(rows: list[dict]) -> str:
    lines = ["| Truy vấn | Đợt | Trung vị (ms) | Min | Max | Node chính | Shared hit | Shared read |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        scans = [n["node"] + (f" ({n['index']})" if n["index"] else "") for n in r["nodes"]
                 if "Scan" in n["node"] and n["relation"] in ("orders", None)]
        lines.append(f"| {r['query']} | {r['phase']} | {r['median_ms']} | {r['min_ms']} | {r['max_ms']} | "
                     f"{'; '.join(scans) or r['nodes'][0]['node']} | {r['shared_hit']} | {r['shared_read']} |")
    return "\n".join(lines)
