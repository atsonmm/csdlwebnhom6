"""Đo EXPLAIN (ANALYZE, BUFFERS) trước/sau 2 chỉ mục của migration 0008 (Task G2).

    cd backend
    .venv/Scripts/python.exe scripts/explain_bench.py --database-url postgresql+psycopg://ticketnhip:ticketnhip@localhost/ticketnhip_large --runs 5

In bảng Markdown (dán vào database/docs/hieu-nang.md) và lưu kế hoạch đầy đủ vào database/docs/plans/.
CẢNH BÁO: tạm DROP rồi tạo lại 2 chỉ mục trên CSDL được chỉ định — không chạy trên CSDL đang phục vụ người dùng.
"""
import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app import perf_bench  # noqa: E402
from app.config.database import make_engine  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default=str(BACKEND.parent / "database" / "docs" / "plans"))
    args = ap.parse_args()
    engine = make_engine(args.database_url)
    engine.echo = False
    rows = perf_bench.run(engine, runs=args.runs, out_dir=Path(args.out))
    print(perf_bench.to_markdown(rows))


if __name__ == "__main__":
    main()
