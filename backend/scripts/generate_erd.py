"""Sinh sơ đồ ERD từ lược đồ THẬT của CSDL (đọc qua SQLAlchemy inspect) → database/docs/erd.svg (+ erd.png, erd.pdf).

    cd backend
    .venv/Scripts/python.exe scripts/generate_erd.py [--database-url <URL>] [--chrome <đường dẫn chrome.exe>]

- Mỗi bảng một khung: tên bảng (+ chú thích tiếng Việt), từng cột với kiểu, PK (khoá chính), FK (khoá ngoại),
  NN (NOT NULL); bảng được nhóm theo miền nghiệp vụ (tài khoản · danh mục · sơ đồ · bán vé).
- Mỗi khoá ngoại một đường nối từ cột của bảng con tới bảng cha, đầu bảng con có ký hiệu "N", đầu bảng cha "1"
  (khoá ngoại nhiều cột — vd. (event_id, show_id) → shows — vẽ một đường, ghi đủ các cột).
- PNG / PDF được chụp bằng Chrome/Edge headless (không cần cài Graphviz).
"""
import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
OUT_DIR = BACKEND.parent / "database" / "docs"

# Bố cục: 4 cột theo miền nghiệp vụ (thứ tự từ trên xuống)
LAYOUT = [
    ("Tài khoản & Ban tổ chức", "#2f6f4f", ["users", "sessions", "password_resets", "organizers", "withdrawals"]),
    ("Danh mục sự kiện", "#8a4b12", ["categories", "events", "home_slots"]),
    ("Suất · hạng vé · sơ đồ", "#3b4f8f", ["shows", "ticket_tiers", "venue_maps", "map_groups", "map_zones", "map_seats"]),
    ("Bán vé", "#8f2f3b", ["coupons", "orders", "order_items", "tickets", "tier_stock", "seat_holds"]),
]
COL_W, ROW_H, HEAD_H, GAP_Y, GAP_X, MARGIN, TITLE_H = 330, 17, 40, 34, 120, 40, 90


def short_type(t) -> str:
    s = str(t).lower()
    return (s.replace("character varying", "varchar").replace("timestamp with time zone", "timestamptz")
             .replace("time without time zone", "time").replace("double precision", "float8"))


def collect(url: str) -> dict:
    eng = create_engine(url)
    insp = inspect(eng)
    tables = {}
    with eng.connect() as conn:
        comments = dict(conn.execute(text(
            "SELECT c.relname, obj_description(c.oid) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r'")).all())
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        views = insp.get_view_names()
    for name in insp.get_table_names():
        if name == "alembic_version":
            continue
        pk = set(insp.get_pk_constraint(name)["constrained_columns"])
        fks = insp.get_foreign_keys(name)
        fk_cols = {c for fk in fks for c in fk["constrained_columns"]}
        cols = [{"name": c["name"], "type": short_type(c["type"]), "pk": c["name"] in pk, "fk": c["name"] in fk_cols,
                 "nn": not c["nullable"]} for c in insp.get_columns(name)]
        tables[name] = {"cols": cols, "fks": fks, "comment": comments.get(name) or ""}
    eng.dispose()
    return {"tables": tables, "version": version, "views": views}


def build_svg(data: dict) -> tuple[str, int, int]:
    tables = data["tables"]
    pos: dict[str, tuple[float, float, float]] = {}  # tên → (x, y, cao)
    colors: dict[str, str] = {}
    heights = []
    placed = set()
    for ci, (_title, color, names) in enumerate(LAYOUT):
        x = MARGIN + ci * (COL_W + GAP_X)
        y = MARGIN + TITLE_H
        for n in names:
            if n not in tables:
                continue
            h = HEAD_H + ROW_H * len(tables[n]["cols"]) + 8
            pos[n] = (x, y, h)
            colors[n] = color
            placed.add(n)
            y += h + GAP_Y
        heights.append(y)
    missing = sorted(set(tables) - placed)  # bảng mới chưa có trong LAYOUT → thêm vào cột cuối
    for n in missing:
        x = MARGIN + 3 * (COL_W + GAP_X)
        y = heights[-1]
        h = HEAD_H + ROW_H * len(tables[n]["cols"]) + 8
        pos[n], colors[n] = (x, y, h), "#555"
        heights[-1] = y + h + GAP_Y
    width = MARGIN * 2 + 4 * COL_W + 3 * GAP_X
    height = max(heights) + 150

    def row_y(t: str, col: str) -> float:
        x, y, _h = pos[t]
        idx = next(i for i, c in enumerate(tables[t]["cols"]) if c["name"] == col)
        return y + HEAD_H + ROW_H * idx + ROW_H / 2 + 2

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'font-family="Segoe UI, Arial, sans-serif">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           f'<text x="{MARGIN}" y="{MARGIN + 6}" font-size="26" font-weight="700" fill="#1c1914">ERD — CSDL TicketNhịp '
           f'(PostgreSQL 18, migration {html.escape(str(data["version"]))})</text>',
           f'<text x="{MARGIN}" y="{MARGIN + 32}" font-size="14" fill="#555">{len(tables)} bảng · '
           f'{sum(len(t["fks"]) for t in tables.values())} khoá ngoại · PK = khoá chính, FK = khoá ngoại, '
           f'NN = NOT NULL · đường nối: N (bảng con) → 1 (bảng cha)</text>']
    for ci, (title, color, _names) in enumerate(LAYOUT):
        x = MARGIN + ci * (COL_W + GAP_X)
        out.append(f'<text x="{x}" y="{MARGIN + TITLE_H - 14}" font-size="15" font-weight="700" fill="{color}">'
                   f'{html.escape(title.upper())}</text>')

    # đường nối khoá ngoại (vẽ trước để nằm dưới khung bảng)
    lines = []
    for child, t in tables.items():
        for fk in t["fks"]:
            parent = fk["referred_table"]
            if parent not in pos:
                continue
            cx, _cy, _ = pos[child]
            px, py, _ = pos[parent]
            y1 = row_y(child, fk["constrained_columns"][0])
            y2 = row_y(parent, fk["referred_columns"][0])
            if child == parent:
                continue
            if abs(cx - px) < 1:  # cùng cột bố cục → vòng ra bên phải
                x1 = cx + COL_W
                x2 = px + COL_W
                bend = x1 + 26 + (len(lines) % 5) * 8
                d = f"M{x1},{y1} C{bend},{y1} {bend},{y2} {x2},{y2}"
                ends = (x1, y1, 1, x2, y2, 1)
            else:
                left_to_right = cx < px
                x1 = cx + COL_W if left_to_right else cx
                x2 = px if left_to_right else px + COL_W
                mid = (x1 + x2) / 2
                d = f"M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}"
                s = 1 if left_to_right else -1
                ends = (x1, y1, s, x2, y2, -s)
            color = colors[child]
            label = ", ".join(fk["constrained_columns"])
            lines.append((d, color, ends, label, fk.get("options", {}).get("ondelete")))
    for d, color, (x1, y1, s1, x2, y2, s2), _label, _ondel in lines:
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4" stroke-opacity="0.55"/>')
        out.append(f'<text x="{x1 + 5 * s1 - (8 if s1 < 0 else 0)}" y="{y1 - 3}" font-size="10" font-weight="700" fill="{color}">N</text>')
        out.append(f'<text x="{x2 + 5 * s2 - (6 if s2 < 0 else 0)}" y="{y2 - 3}" font-size="10" font-weight="700" fill="{color}">1</text>')
        out.append(f'<circle cx="{x2}" cy="{y2}" r="2.6" fill="{color}"/>')

    for name, t in tables.items():
        x, y, h = pos[name]
        color = colors[name]
        out.append(f'<g><rect x="{x}" y="{y}" width="{COL_W}" height="{h}" rx="6" fill="#fffdf8" stroke="{color}" stroke-width="1.5"/>')
        out.append(f'<rect x="{x}" y="{y}" width="{COL_W}" height="{HEAD_H - 4}" rx="6" fill="{color}"/>')
        out.append(f'<text x="{x + 10}" y="{y + 16}" font-size="14" font-weight="700" fill="#fff">{html.escape(name)}</text>')
        note = t["comment"]
        note = note if len(note) <= 52 else note[:50] + "…"
        out.append(f'<text x="{x + 10}" y="{y + 30}" font-size="10" fill="#fff" fill-opacity="0.9">{html.escape(note)}</text>')
        for i, c in enumerate(t["cols"]):
            ry = y + HEAD_H + ROW_H * i + ROW_H - 3
            if i % 2 == 0:
                out.append(f'<rect x="{x + 1}" y="{ry - ROW_H + 4}" width="{COL_W - 2}" height="{ROW_H}" fill="#f4efe6"/>')
            badge = ("PK " if c["pk"] else "") + ("FK" if c["fk"] else "")
            weight = "700" if c["pk"] else "400"
            out.append(f'<text x="{x + 8}" y="{ry}" font-size="9.5" font-weight="700" fill="{color}">{badge.strip()}</text>')
            out.append(f'<text x="{x + 44}" y="{ry}" font-size="12" font-weight="{weight}" fill="#1c1914">{html.escape(c["name"])}</text>')
            typ = c["type"] + (" NN" if c["nn"] and not c["pk"] else "")
            out.append(f'<text x="{x + COL_W - 8}" y="{ry}" font-size="11" fill="#6b6257" text-anchor="end">{html.escape(typ)}</text>')
        out.append("</g>")

    vy = height - 110
    out.append(f'<text x="{MARGIN}" y="{vy}" font-size="14" font-weight="700" fill="#1c1914">VIEW</text>')
    out.append(f'<text x="{MARGIN}" y="{vy + 22}" font-size="12" fill="#333">'
               + html.escape(" · ".join(data["views"])) + " (dựa trên orders, order_items, tickets, events)</text>")
    out.append(f'<text x="{MARGIN}" y="{vy + 46}" font-size="12" fill="#333">Ràng buộc nổi bật: CHECK trạng thái / số tiền / '
               "kho (presold + sold ≤ capacity), khoá ngoại nhiều cột (order_id, event_id) giữ vé và dòng đơn cùng sự kiện, "
               "UNIQUE email / SĐT / slug, chỉ mục GIN trigram tìm đơn (0008).</text>")
    out.append(f'<text x="{MARGIN}" y="{vy + 70}" font-size="11" fill="#777">Sinh tự động bằng backend/scripts/generate_erd.py '
               "từ lược đồ thật (SQLAlchemy inspect) — chạy lại sau mỗi migration.</text>")
    out.append("</svg>")
    return "\n".join(out), width, height


def find_chrome(given: str | None) -> str | None:
    cands = [given, shutil.which("chrome"), shutil.which("msedge"),
             "C:/Program Files/Google/Chrome/Application/chrome.exe",
             "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"]
    return next((c for c in cands if c and Path(c).exists()), None)


def main() -> None:
    from app.config.settings import settings

    ap = argparse.ArgumentParser(description="Sinh ERD (SVG + PNG + PDF) từ lược đồ CSDL")
    ap.add_argument("--database-url", default=settings.database_url)
    ap.add_argument("--chrome")
    a = ap.parse_args()
    data = collect(a.database_url)
    svg, w, h = build_svg(data)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = OUT_DIR / "erd.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"Đã ghi {svg_path} ({len(data['tables'])} bảng)")
    chrome = find_chrome(a.chrome)
    if not chrome:
        print("Không thấy Chrome/Edge — chỉ có erd.svg (mở bằng trình duyệt rồi in ra PNG/PDF)")
        return
    page = OUT_DIR / "_erd_print.html"
    page.write_text(f"<!doctype html><meta charset='utf-8'><style>@page{{size:{w}px {h}px;margin:0}}"
                    f"html,body{{margin:0}}</style>{svg}", encoding="utf-8")
    url = page.resolve().as_uri()
    try:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1.5",
                        f"--window-size={w},{h}", f"--screenshot={OUT_DIR / 'erd.png'}", url], check=True,
                       capture_output=True, timeout=120)
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT_DIR / 'erd.pdf'}", url], check=True, capture_output=True, timeout=120)
    finally:
        page.unlink(missing_ok=True)
    print(f"Đã ghi {OUT_DIR / 'erd.png'} và {OUT_DIR / 'erd.pdf'}")


if __name__ == "__main__":
    main()
